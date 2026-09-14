# Contributing

This is a portfolio reference implementation with one author, and it is public so that its record
can be read. Issues and pull requests are welcome; the rules below are the ones the author works
under, and CI enforces most of them.

## Setup

```bash
uv sync --extra contracts --extra agent      # the local gate
uv sync --extra spark --extra dbt            # silver's and gold's tests, ~700 MB and a JVM
make check                                   # lint · typecheck · contracts · the four document gates · the suite
```

## The rules that are gates

- **All repository content is in English.** `make language` refuses Greek outside the declared
  exceptions.
- **Never commit to `main`.** One branch per closed piece of work, a pull request, CI green,
  squash-merge. The `main` ruleset requires an up-to-date branch and one aggregate check.
- **A generated artefact is never hand-edited.** `make contracts` recompiles everything under
  `generated/` and fails when what is on disk differs.
- **A finding anchors to a line, a deferral names its unlock condition or a date, a figure in
  prose is re-run.** `make findings`, `make expiry`, `make figures`.
- **A gate is proved to bite.** A new check in an eval owns at least one mutation under
  `evals/gate_proof/mutations/claim-N/`, refused by that check by name.
- **A correction never erases what was previously stated.** Restate below the prior wording,
  dated, with the delta; `CLAUDE.md`'s doctrine rule 4.

## What a pull request is reviewed against

[`CLAUDE.md`](CLAUDE.md) — the claims, the doctrine, and the checklist under *Before any change*.
A reviewer in fresh context reads the diff against it; the findings go to
[`docs/FINDINGS.md`](docs/FINDINGS.md) with a site and a disposition.

## What you cannot do from a fork

Anything that reaches the estate. The five dispatch workflows run from `main` only, under the
repository's own environments and role.
