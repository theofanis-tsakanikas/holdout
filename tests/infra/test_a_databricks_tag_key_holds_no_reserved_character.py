"""A model serving endpoint's tag key carries no character its API reserves.

    cannot create model serving: Endpoint tag key holdout:project is either not between
    1-255 characters long or contains one or more of the reserved characters: . , = / or :

**Every object in this estate carries `holdout:project`.** It is what the budget's cost filter
matches, what `infra/foundation/reaper/reap.py` enumerates, and what `destroy`'s survivor list
reads — one key, deliberately, so that four mechanisms agree about what belongs to this project.
Model serving refuses a colon in a tag key, so that one object cannot carry it.

**What made this expensive is where it surfaced.** The endpoint is applied by `backfill`, at the
end, after the baseline, the comparison window, two passes of silver and gold, training, the
promotion gates and a registered model version. Everything upstream had to succeed before a
character in a string could fail — about forty minutes to learn that a colon is reserved.

## What this asserts, and why the population is one resource

Every `tags { key = "…" }` block inside a `databricks_model_serving` uses a key free of `.` `,`
`=` `/` and `:`.

**The restriction is per-resource, and the first version of this gate got that wrong.** Written
over every Databricks tag block it went red against `infra/lakehouse/warehouse.tf`, which carries
`holdout:project` and **applies** — measured, on the estate, today: the warehouse exists and dbt
ran against it. A gate that refuses a resource the platform accepts is not a stricter gate; it is
a wrong one, and it would have been "fixed" by changing a key that never needed changing.

AWS `default_tags` are a third population, written as a map, and AWS accepts the colon — which is
why the estate's own key has one.

## What it does not check

- **It does not check the value**, only the key. The API's message names the key, and a value that
  offends will name itself the same way.
- **It does not check that the object is tagged at all.** An untagged endpoint is a different
  finding — the one this register already holds about the network Databricks leaves behind — and
  it belongs to whatever enumerates that population, not to a reader of Terraform text.
"""

from __future__ import annotations

import re

import pytest

from tests.infra import tasks

#: The five the API names, and it names them in the error rather than in a table anyone had read.
RESERVED = ".,=/:"

#: The resource whose API refused, named rather than generalised. Another that refuses joins it
#: when it refuses; a list written ahead of the evidence is a list this repository files findings
#: about.
RESOURCE = "databricks_model_serving"

_COMMENT = re.compile(r"^\s*#.*$", re.MULTILINE)
_RESOURCE = re.compile(rf'resource\s+"{RESOURCE}"\s+"[^"]+"\s*\{{(.*?)\n\}}', re.DOTALL)
_TAG_KEY = re.compile(r"tags\s*\{[^}]*?key\s*=\s*\"([^\"]*)\"", re.DOTALL)


def _keys() -> list[tuple[str, str]]:
    """Every `(where, key)` a model serving resource tags with, comments removed first."""
    found: list[tuple[str, str]] = []
    for path in tasks.files():
        text = _COMMENT.sub("", path.read_text(encoding="utf-8"))
        for body in _RESOURCE.findall(text):
            found.extend(
                (str(path.relative_to(tasks.REPO_ROOT)), key) for key in _TAG_KEY.findall(body)
            )
    return found


KEYS = _keys()


def test_there_is_a_tag_block_to_check() -> None:
    """An empty population passes every assertion below it and proves nothing."""
    assert KEYS, (
        f"no `{RESOURCE}` under infra/ carries a tag block. Either the endpoint is untagged — "
        "which is a finding of its own, because an object nothing enumerates is an object nothing "
        "reaps — or this reader stopped seeing it."
    )


@pytest.mark.parametrize(("where", "key"), KEYS, ids=[f"{w}::{k}" for w, k in KEYS])
def test_a_tag_key_holds_no_reserved_character(where: str, key: str) -> None:
    offending = sorted({character for character in key if character in RESERVED})
    assert not offending, (
        f"{where} tags with `{key}`, which holds {offending}.\n\n"
        f"Databricks reserves {list(RESERVED)} in a tag key and refuses the whole resource. The "
        "estate's own key is `holdout:project` because AWS accepts a colon; a Databricks object "
        "cannot carry it and needs a spelling of its own, with the reason beside it."
    )
