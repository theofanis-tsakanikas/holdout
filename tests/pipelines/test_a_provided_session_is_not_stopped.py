"""A session this repository did not build is used and not stopped.

**Serverless compute is Spark Connect and the session exists before the task's first line.**
Databricks' own limitations page says only Spark Connect APIs are supported there, which rules out
everything the local builders configure: `.master("local[2]")`, `spark.sql.extensions`,
`spark.sql.catalog.spark_catalog`, a Derby metastore, and `configure_spark_with_delta_pip` from a
`delta` package the serverless environment does not carry. So on the estate `build` has to return
what the runtime already has.

**And then it must not stop it.** `spark.stop()` on the runtime's session does not raise — it ends
the compute out from under whatever the job runs next, which is a failure in a task that did
nothing wrong. Ownership is recorded on the session itself, by a config only the local builders
set, because ownership tracked anywhere else is a second thing to keep in step.

## What it does not check

- **It does not check serverless.** There is no serverless in a test run; what is measured here is
  that a session presented as the runtime's survives, and that a locally built one is stopped.
"""

from __future__ import annotations

from typing import Any

import pytest

from pipelines import session as runtime


class _Stub:
    """A session that records whether it was stopped, and answers `conf.get` like Spark's."""

    def __init__(self, local: str | None) -> None:
        self._local = local
        self.stopped = False
        outer = self

        class _Conf:
            def get(self, key: str, default: Any = None) -> Any:
                if key == runtime.LOCAL and outer._local is not None:
                    return outer._local
                return default

        self.conf = _Conf()

    def stop(self) -> None:
        self.stopped = True


def test_release_stops_a_session_this_repository_built() -> None:
    spark = _Stub("true")
    runtime.release(spark)
    assert spark.stopped, (
        "a locally built session was not stopped. Every local session holds a JVM and a Derby "
        "metastore; a suite that leaks one per test runs out of both."
    )


def test_release_leaves_a_session_it_did_not_build_alone() -> None:
    spark = _Stub(None)
    runtime.release(spark)
    assert not spark.stopped, (
        f"a session with no `{runtime.LOCAL}` marker was stopped. On the estate that is the "
        "runtime's own session: stopping it ends the compute under the tasks that follow, and "
        "the failure lands on one of them rather than here."
    )


@pytest.mark.parametrize("marker", ["false", "0", ""])
def test_release_leaves_a_session_that_says_it_is_not_ours(marker: str) -> None:
    spark = _Stub(marker)
    runtime.release(spark)
    assert not spark.stopped, f"`{runtime.LOCAL}={marker!r}` was read as ownership."


@pytest.mark.silver
def test_a_local_session_marks_itself_and_is_found_again() -> None:
    """The two halves measured against a real session rather than a stub.

    Marked `silver` because it starts one: the engine is an extra, and
    `tests/boundary/test_the_engine_is_never_skipped.py` refuses the spelling that would have
    made this a skip instead. The three above need no engine and run in the ordinary suite.
    """
    from pipelines.silver import session

    spark = session.build("holdout-session-ownership")
    try:
        assert spark.conf.get(runtime.LOCAL, "false") == "true", (
            "the local builder did not set the ownership marker, so `release` would leave every "
            "session it builds running."
        )
        assert session.build("holdout-session-ownership-again") is spark, (
            "a second build made a second session while one was active. On the estate that is "
            "the branch that must return the runtime's session instead of configuring its own."
        )
    finally:
        spark.stop()
