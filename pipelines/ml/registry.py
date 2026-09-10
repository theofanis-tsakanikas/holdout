"""Turning a trained model into a Unity Catalog version — and refusing when a gate refused.

**Nothing in this repository logged a model before this file existed.** `infra/ml/training.tf`
declares a `databricks_registered_model` and its own description says *registers a version only if
they pass*; `backfill.yml` then reads `databricks model-versions list` and takes the highest
version, and `infra/serving` points an endpoint at it. Every one of those steps was written
against a version that nothing created: `grep -r mlflow` over `pipelines/`, `src/` and `ops/`
returned nothing at all. The training job trained, printed its assessment, and exited zero.

**A refused model is not registered, and that is the whole of doctrine rule 5 here.** A version in
the registry is a thing `backfill` will serve within the same run — so creating one for a model
whose gates refused would promote it by arithmetic, `max(version)`, with nobody having decided
anything. `promotion.Promotion` is the type that names a human; this function's job is to make
sure the registry never holds a candidate that type could not be built for.

**`mlflow` is imported inside the function.** It is the estate's package, present in the
serverless environment and absent from this repository's own dependency groups: at module scope,
importing `pipelines.ml.registry` on a laptop would fail, and `pipelines/ml/__main__.py` imports
it only on the branch that was given a model name.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipelines.ml.build import TrainingRun

#: The repository root, from this file's own location: `pipelines/ml/registry.py`.
#:
#: **Not from the entrypoint's `here()`**, which exists because a `spark_python_task` `exec`s a
#: file and binds no `__file__`. This module is *imported*, and an imported module always has
#: one — the two are different questions and conflating them would put a fallback here that
#: nothing can ever exercise.
_ROOT = Path(__file__).resolve().parents[2]

#: The four columns `model.DemandModel.predict` takes, in the order the signature declares them.
#: Written once here because the wrapper, the example and the signature must agree, and three
#: copies of a column list is three places to forget one.
FEATURES: tuple[str, ...] = ("sku_id", "weekday", "store_id", "category")


class RefusedError(RuntimeError):
    """A gate refused, so there is no version to create. Raised rather than returned.

    The training job's exit code is what `backfill` reads, and a refusal that exited zero would
    let the next step look for a version that was never made and report a missing parameter
    instead of a refused model.
    """


def _example(run: TrainingRun) -> list[dict[str, Any]]:
    """One real row from the training build, as the input example the registry stores.

    Real rather than invented: Unity Catalog requires a signature, a signature is inferred from
    an example, and an example whose category or weekday the model never saw would be a
    demonstration of the model failing rather than of it answering.
    """
    feature = run.build.features[0]
    return [
        {
            "sku_id": feature.sku_id,
            "weekday": int(feature.weekday),
            "store_id": feature.store_id,
            "category": feature.category,
        }
    ]


def register(run: TrainingRun, *, model_name: str, experiment: str | None = None) -> int:
    """Log the model and create a version of `model_name`. Returns the version number."""
    # **The refusal is decided before mlflow is imported**, so the gate that proves it can run
    # on a machine that has no mlflow — which is every machine except the estate's.
    if not run.assessment.passed:
        refused = ", ".join(gate.id for gate in run.assessment.refusals)
        raise RefusedError(
            f"{len(run.assessment.refusals)} of {len(run.assessment.gates)} gates refused "
            f"({refused}), so no version is created. A registered version is one `backfill` "
            "serves in the same run: creating one here would promote a refused model by "
            "arithmetic."
        )

    import mlflow
    import pandas as pd
    from mlflow.models import infer_signature

    class Demand(mlflow.pyfunc.PythonModel):  # type: ignore[misc]
        """The repository's own model, answering the estate's calling convention.

        `DemandModel.predict` takes keyword arguments and returns a `Fraction`, because exactness
        is what the rest of this repository is about. An endpoint returns JSON, so the boundary
        is here: one conversion, at the edge, named.
        """

        def __init__(self, model: Any) -> None:
            self._model = model

        def predict(
            # `context` and `params` are mlflow's calling convention and neither is used here:
            # the model carries its own numbers and takes no inference-time parameters.
            self,
            context: Any,  # noqa: ARG002
            model_input: Any,
            params: Any = None,  # noqa: ARG002
        ) -> list[float]:
            return [
                float(
                    self._model.predict(
                        sku_id=str(row.sku_id),
                        weekday=int(row.weekday),
                        store_id=str(row.store_id),
                        category=str(row.category),
                    )
                )
                for row in model_input.itertuples()
            ]

    wrapper = Demand(run.model)
    example = pd.DataFrame(_example(run))
    signature = infer_signature(example, wrapper.predict(None, example))

    # **Unity Catalog, not the workspace registry**, matching `infra/ml/training.tf`: the
    # registered model there is a three-level name and only this registry uri understands one.
    mlflow.set_registry_uri("databricks-uc")
    if experiment:
        mlflow.set_experiment(experiment)

    with mlflow.start_run():
        for name, value in run.summary:
            mlflow.log_param(name.replace(" ", "_"), value)
        mlflow.set_tag("holdout.model_digest", run.assessment.model_digest)
        mlflow.set_tag("holdout.gates_passed", str(len(run.assessment.gates)))
        info = mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=wrapper,
            signature=signature,
            input_example=example,
            registered_model_name=model_name,
            # **The model carries the code that defines it, or it cannot be loaded anywhere
            # else.**
            #
            # `Demand` above is defined inside this function, so cloudpickle stores it *by
            # value* — the serving container needs nothing to reconstruct the wrapper. What it
            # holds is a `DemandModel`, and that class lives in `pipelines.ml.model`, which is
            # importable here and therefore stored **by reference**. A serving endpoint has this
            # repository nowhere on its path, so loading it raises `ModuleNotFoundError` inside
            # the container and the endpoint reports `UPDATE_FAILED` with the reason on a page.
            #
            # Measured: the first endpoint spent eight minutes reaching that state, at the end of
            # a backfill that had loaded a baseline, a window, trained and registered a version.
            #
            # `code_paths` copies these into the model's artifact and puts them on `sys.path` at
            # load, so the version in the registry carries the code that produced it rather than
            # a reference to a checkout that exists on one machine. Absolute, because the task's
            # working directory is the runtime's business and this file's location is not.
            code_paths=[str(_ROOT / "pipelines"), str(_ROOT / "src" / "holdout")],
        )

    version = getattr(info, "registered_model_version", None)
    if version is None:
        # Older clients do not carry it on the ModelInfo; the registry is the authority either
        # way, and asking it is one call rather than a version check on the client.
        from mlflow.tracking import MlflowClient

        versions = MlflowClient().search_model_versions(f"name='{model_name}'")
        version = max(int(candidate.version) for candidate in versions)
    return int(version)
