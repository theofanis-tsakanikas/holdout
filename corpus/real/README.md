# `corpus/real/` — prices this project did not choose

Claim 1's trap is that *a planter reading the same contract as the detector is one function
agreeing with itself*. This directory is the answer to it: real retail prices, a real
regulated-goods list and a real industry margin, all published by people who have never seen
this repository.

**Nothing here imports `holdout`.** No refusal code, no `Money`, no opinion about whether a
price is admissible. `tests/boundary/test_corpus_imports_nothing.py` fails the build if that
ever changes, for the same reason `corpus/world/` will be held to it: a corpus that can reach
the gates it exists to attack has stopped being independent of them, and it would stop
gradually, by the ordinary drift of whoever is editing both. The join between the two lives
in `evals/guardrail/build.py`.

`MANIFEST.yaml` is the authority on every source — URL, licence, retrieval date, digest, what
was dropped and why. `tests/corpus/test_manifest.py` recomputes every digest, so the corpus
cannot be edited without something going red. This file is the summary.

---

## What is in it

| | rows | what it is |
|---|---|---|
| `data/ons-price-quotes-2025.csv.gz` | 32,480 | individual price quotes collected by hand in UK shops, February–July 2025 |
| `data/greek-regulated-basket-2026.csv` | 63 | the categories under the Greek gross-margin cap, ΦΕΚ Β΄ 1411/12.03.2026 |
| `data/eurostat-sbs-gross-margin-el.csv` | 13 | gross margin on goods for resale, Greek supermarkets, 2008–2020 |
| `data/item_categories.csv` | 37 | **ours** — the map from an ONS item to a scenario category and a decision ordinal |

The fourth file is in a separate file from the first three because it is the only one this
repository wrote. Keeping the line visible in a directory listing is deliberate.

### The prices

Office for National Statistics, published under the Open Government Licence v3.0. One row is
one product, in one outlet, in one month — a price a person wrote down in a shop. Not a
survey average, not modelled.

37 representative items across seven scenario categories, 811 outlet strata, five months.
Within it: 1,577 quotes the collector flagged as a sale or special offer — **real markdowns
taken by real retailers**, at a median depth of 14.6% and a maximum of 50.4%; a real
distribution of price endings, with `.00`, `.50`, `.25`, `.75`, `.95` and `.99` all heavily
represented; and real month-to-month price moves for the same product in the same outlet.

The price endings matter more than they look. The one bug this project's own review found by
composing two modules was a half-cent disagreement that showed up on every base price ending
in five — which is one price in five, in real data, and would have been zero in a corpus of
round numbers.

Three categories are here to be *refused*, not priced: cigarettes, spirits, infant formula
and fresh fish are frozen in the scenario, so their real prices are what
`G5.frozen-category-never-certified` is driven with.

### The regulated list

ΥΑ 21330/12.03.2026, ΦΕΚ Β΄ 1411, άρθρο 6 — the table of sixty-three categories of goods
"necessary for consumers' nutrition and living", under the cap imposed by the ΠΝΠ of
11.03.2026.

`contracts/guardrails/regulated_basket.yaml` names three categories and declares them a
`scenario_assumption`, because when it was written this decision **had not been obtained**.
It has been now, and the corpus therefore disagrees with the contract. That is the point.

*Declared limit:* the ΦΕΚ PDF itself was not reached. The text was read at a legal-database
reproduction, the gazette reference is stated identically by three independent legal
databases, and the list was cross-checked against an independent prose enumeration in the
press, which agrees item for item. That is the same limit `docs/REGULATORY.md` already
records for every Greek citation here, and it is on the publication checklist.

### The margin, and the cost that is derived from it

**A retailer's unit cost is not public and never will be.** It is what a buyer negotiates. So
the corpus takes a real published statistic for the right industry in the right country —
Eurostat's gross margin on goods for resale over turnover for NACE 47.11, Greece — and the
eval derives `unit_cost = price × (1 − m)` with `m = 0.1681`, the median of the thirteen
published years.

A median rather than a mean because the 2018 observation is a break in the series: 47.8%
against roughly 17% either side of it. The row stays in the file. Deleting it would have made
the number honest by accident, and the reasoning above would then describe a decision nobody
had to make. `tests/corpus/test_manifest.py` asserts the row is still there.

Eurostat's ratio is a margin over turnover, which is the same quantity άρθρο 4 παρ. 4 of the
Greek decision calls **ΠΜΚ** — margin over the selling price. That alignment is not a
coincidence and it is what makes the conversion in `evals/guardrail/build.py` exact.

---

## Rebuilding it

```
make corpus     downloads ~100 MB from the ONS and rewrites data/
```

Needs the network, and **CI never runs it**. The data is committed and digest-checked
instead, because an eval that downloaded its own corpus would stop being reproducible the day
a source moved, and would stop running on a laptop with no network — which is the one
property every claim in this repository depends on.

`fetch.py` exists so the provenance is a command rather than a description. It prints what it
kept and what it dropped, so a rebuild that quietly loses half the corpus is visible.

---

## Attribution

Contains public sector information licensed under the Open Government Licence v3.0. Source:
Office for National Statistics licensed under the Open Government Licence. The ONS states
these figures are for research purposes only and are not accredited official statistics;
nothing in this repository draws a conclusion about UK inflation.

Eurostat data is reused under the Eurostat reuse policy, which authorises reuse provided the
source is acknowledged.
