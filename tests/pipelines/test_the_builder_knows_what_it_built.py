"""A session this repository did not build is used and not stopped, and nothing is asked to prove it.

**Serverless compute is Spark Connect and the session exists before the task's first line.** So
`sessions()` returns the runtime's where there is one, and builds a local Delta session where
there is not. **And then it must not stop what it did not build**: `spark.stop()` on the
runtime's session does not raise, it ends the compute out from under whatever the job runs next.

**The first version asked the session which kind it was.** The local builders set a config,
`spark.holdout.session.local`, and `release` read it back with a default of `"false"` — the
argument being that ownership recorded anywhere else is a second thing to keep in step. On the
estate that read is refused:

    AnalysisException: [CONFIG_NOT_AVAILABLE.WITHOUT_SUGGESTION]
    Configuration spark.holdout.session.local is not available.  SQLSTATE: 42K0I

**A default argument is not a default there.** `spark.conf.get(key, default)` raises for a key the
platform does not know rather than returning what it was handed. The module written so that the
estate's session would not be stopped failed on being asked whether to stop it — in the silver
job, after the baseline had loaded thirty-three million rows.

> **The knowledge was never the session's to hold.** The code that decides whether to build one is
> the code that knows whether it did. A `with` block carries that and asks nobody.

## What it does not check

- **It does not check serverless.** There is no serverless in a test run. What is measured is that
  a session presented as the runtime's survives the block, and that a locally built one does not.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest

from pipelines import session as runtime

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyspark.sql import SparkSession


def _as_session(stub: _Stub) -> Callable[[], SparkSession]:
    """The stub, typed as what `owned` builds. It answers the two calls `owned` makes."""
    return lambda: cast("SparkSession", stub)


class _Stub:
    """A session that records whether it was stopped, and refuses `conf` the way the estate does."""

    def __init__(self) -> None:
        self.stopped = False
        self.conf = _RefusingConf()

    def stop(self) -> None:
        self.stopped = True


class _RefusingConf:
    """`spark.conf.get` on serverless, for a key the platform does not know."""

    def get(self, key: str, default: Any = None) -> Any:
        raise RuntimeError(
            f"[CONFIG_NOT_AVAILABLE.WITHOUT_SUGGESTION] Configuration {key} is not available."
        )


def test_a_provided_session_is_yielded_and_left_running(monkeypatch: pytest.MonkeyPatch) -> None:
    provided = _Stub()
    monkeypatch.setattr(runtime, "provided", lambda: cast("SparkSession", provided))

    def refuse() -> SparkSession:  # pragma: no cover - reaching this is the failure
        pytest.fail("a session was built while the runtime already had one")

    with runtime.owned(refuse) as spark:
        assert spark is cast("SparkSession", provided)
    assert not provided.stopped, (
        "the runtime's own session was stopped. On the estate that ends the compute under the "
        "tasks that follow, and the failure lands on one of them rather than here."
    )


def test_a_session_built_here_is_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime, "provided", lambda: None)
    built = _Stub()

    with runtime.owned(_as_session(built)) as spark:
        assert spark is cast("SparkSession", built)
    assert built.stopped, (
        "a locally built session was not stopped. Every local session holds a JVM and a Derby "
        "metastore; a suite that leaks one per test runs out of both."
    )


def test_nothing_asks_the_session_which_kind_it_is(monkeypatch: pytest.MonkeyPatch) -> None:
    """The estate's refusal, reproduced: `conf.get` raises and the block must not care."""
    monkeypatch.setattr(runtime, "provided", lambda: None)
    built = _Stub()

    with (
        runtime.owned(_as_session(built)) as spark,
        pytest.raises(RuntimeError, match="CONFIG_NOT_AVAILABLE"),
    ):
        spark.conf.get("spark.holdout.session.local", "false")

    assert built.stopped, (
        "the session was not stopped, which means something read `conf` to decide and swallowed "
        "the refusal. Ownership is lexical: `owned` built this one and closes it."
    )


@pytest.mark.silver
def test_a_local_session_is_found_again_while_one_is_open() -> None:
    """Measured against a real session rather than a stub.

    Marked `silver` because it starts one: the engine is an extra, and
    `tests/boundary/test_the_engine_is_never_skipped.py` refuses the spelling that would have made
    this a skip instead. The three above need no engine and run in the ordinary suite.
    """
    from pipelines.silver import session

    with session.sessions("holdout-session-ownership") as spark:
        assert runtime.provided() is spark, (
            "with a session open, `provided` did not find it. On the estate that is the branch "
            "that must return the runtime's session instead of configuring its own."
        )
