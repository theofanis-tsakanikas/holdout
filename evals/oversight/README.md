# Claim 7 — a decision that targets a person is structurally impossible

> The decision key has no customer dimension, and a test goes red if one appears.
>
> *Trap — written down here for the first time: **a list of person-shaped words written by
> whoever also wrote the field names is one function agreeing with itself.** It contains
> exactly the words its author thought of while looking at the fields they had just written,
> so it is guaranteed to find nothing and guaranteed to feel like a guard.*

```
make claim-7          the eval, and the seven mutations claim 7 owns  ~36 s
make eval-oversight   the eval alone                                  ~4 s
```

Claim 7's row in `CLAUDE.md` was the one row in the table of seven with no trap beside it.
That is not a formatting omission — it is where the defect was. Six other claims had somebody
write down what agreeing with itself would look like; this one had a word list, and nobody had
asked who wrote it.

---

## 1 · What is attacked

Three hundred and seventeen names that two published vocabularies use for a person are
planted, one at a time, on every one of the fifty-six types a decision passes through —
**17,752 attacks** — and the question is who refuses.

| id | the question it would answer `false` |
|---|---|
| `O1.the-key-is-what-is-priced-and-where` | is a decision addressed by a SKU, a store, a path and an occasion, those four and nothing else? |
| `O2.every-decision-path-type-carries-exactly-the-fields-written-down` | does every type carry exactly the fields a human wrote down beside it? |
| `O3.every-type-in-the-core-is-written-down` | can claim 7 be defeated by adding a *type* rather than a field? |
| `O4.no-field-is-a-name-a-person-is-known-by` | does any of the 242 fields carry one of the 317 published names? |
| `O5.no-new-identifier-in-the-package-is-a-name-a-person-is-known-by` | and any of the 1,181 identifiers `src/holdout/` defines — parameters and enum members included? |
| `O6.every-planted-person-is-refused` | planting each name on each type, does the structural assertion refuse every one? |
| `O7.the-word-list-never-refuses-alone` | is the hand-written word list ever the *only* thing that catches an attack? |
| `O8.the-scan-reaches-the-types-that-are-not-dataclasses` | do the types whose constructors refuse report their fields, or are they invisible? |
| `O9.no-person-can-be-attached-to-a-key-at-runtime` | can a person be stapled to a key by construction, by assignment, or by `replace`? |
| `O10.no-contract-declares-a-customer-dimension` | can a decision become per-customer through a **contract**, with no Python changing? |
| `O11.the-source-text-and-the-live-objects-agree` | does a second reading, parsed rather than imported, produce the same field sets? |
| `O12.every-explanation-still-explains-something` | does any entry on the reviewed list of innocent collisions outlive the thing it explained? |

`O2` is the one that carries the claim, and it is the one that reads no names at all: a field
called `q7` is the same finding as a field called `nationality`. `O4`, `O5` and `O10` bound the
ways `O2` could be passing for the wrong reason, and `O7` is the measurement that says which of
the two mechanisms is actually the guard.

---

## 2 · Where the independence is

Four separations, strongest last.

**The words are not ours.** `corpus/real/` carries 156 schema.org properties whose domain or
range includes `Person` — release 30.0, pinned — and 99 PII entity types Microsoft Presidio
ships recognizers for, pinned at a commit. Two publishers who have never coordinated with
each other and have certainly never read `contracts/`. The extraction from each is mechanical
and total: nothing is curated, nothing is dropped, and both keep the publisher's own spelling.
`DATE_TIME`, `LOCATION`, `brand`, `award`, `height` and `weight` are on those lists and they
stay on them — the moment this repository starts deciding which of somebody else's names count,
the inputs are being chosen here again, which is the trap wearing a filter.

**The half nobody writing a blacklist thinks of.** schema.org publishes two kinds of property
about a person: what a person *has* — `birthDate`, `familyName`, `nationality`, `taxID` — and
what *holds* a person: `customer`, `member`, `buyer`, `owner`, `recipient`, `borrower`,
`underName`. The second kind is the one a pricing system would actually grow, and it is the one
a list written from the inside never contains. The corpus keeps the two apart in separate
columns so a reader can see which is which.

**`corpus/real/` cannot see the system.** It imports nothing from `holdout` — no type, no
field name, no opinion about what a decision is — and
`tests/boundary/test_corpus_imports_nothing.py` fails the build if that ever changes. The join
between the vocabularies and the types lives in `build.py`, in this directory, where it can be
read as one thing.

**The field sets are read twice, by two mechanisms that share nothing.** `ops/personhood.py`
imports each module and asks Python: `dataclasses.fields`, `__slots__`, `getattr`.
`reference.py` never imports one — it parses the source text with `ast` and reads annotated
assignments and string literals. One is blind to everything written down that the import
machinery rewrites; the other is blind to everything created at runtime and never written down.
`O11` publishes the disagreement rather than assuming there is none. The two share exactly one
function, `ops.personhood.tokens`, because how a name is split into words is a *convention* and
not a decision: spelling it twice would be two spellings of one thing, which is what the
contract layer exists to argue against.

### And the guard is a rule with two callers, not a test

`ops/personhood.py` holds the registry and the word list, in the arrangement `ops/isolation.py`
already has for the corpus barrier: one implementation, two callers.
`tests/core/test_decision_key.py` asks *is it true right now*, on every push. This eval asks
*is it still true against 317 names somebody else chose, and does it still refuse when each of
them is planted*. Nothing under `ops/` is ever a mutation target — the planter edits the
**system**, `src/` and `contracts/`, and never the detector.

---

## 3 · Observed, derived, swept

| | |
|---|---|
| **observed** | 156 schema.org properties, 99 Presidio entity types, both committed and digest-checked; the 56 field sets; the 1,181 identifiers; every metric grain, idempotency key and covariate id |
| **derived**, with the arithmetic written out | the *spelling*. `familyName` and `US_SSN` become `family_name` and `us_ssn`, because that is how a field is written here. One further derivation: a Presidio entity whose leading token is a two-letter region code also contributes its remainder, so `DE_TAX_ID` yields `tax_id` as well. It only ever **adds** names, so it errs towards more attacks and never fewer, and the duplicates it creates are collapsed and counted |
| **swept** | the attack grid — the lexicon sorted, the types sorted, their product in that order. Nothing is drawn at random, so a red run reproduces exactly and prints the same counterexamples every time |

---

## 4 · The measurement, which is the whole point

```
attacks planted                          17,752
  refused by the closed field set        17,752
  refused by the hand-written word list  1,960 (35/317 = 11.0% of the names)
```

**The word list this repository was carrying catches eleven per cent of the names two
published vocabularies use for a person.** It misses `family_name`, `given_name`,
`nationality`, `job_title`, `spouse`, `sibling`, `nif`, `aadhaar`, `fiscal_code`,
`passport`, `buyer`, `owner`, `recipient` and 269 others.

Those thirteen are pinned in `tests/evals/test_oversight_instrument.py`, in both directions,
because **the first version of this paragraph was wrong**. It also named `telephone` and
`personnummer`, and the word list catches both: `PERSON_SHAPED` contains `phone` and `person`
and it matches by substring. The aggregate figures — 35, 282, 11.0% — were right the whole
time; the illustrations had been picked by reading the lexicon rather than by asking
`ops.personhood.person_shaped`, the function that would make the sentence true. Found by
oversight level 2, and the prior wording is named here rather than deleted, per doctrine rule
4, because the delta *is* the finding: this is the branch about a guard tested by its author,
and its own prose was written the same way.

That is not an argument for a longer list. A list twice as long would be the same function
agreeing with itself twice as loudly, and the next name would be the one nobody wrote down.
It is the argument for the *structure*: `O2` refuses every one of the 17,752, and it would
refuse a field called `q7` on the same evidence, because it never reads the name at all.

`O7` is that sentence made into a gate: **no attack may ever be caught by the word list
alone.** If one were, claim 7 would be resting on words somebody here chose.

### The eleven explained collisions, published rather than filtered

Ordinary engineering English and the vocabulary of personhood overlap, and hiding the overlap
would mean curating the input. So it is printed in full, with a reason each — nine of them in
`src/holdout/`, two more in the compiled consumers under `generated/`: `AGENT`, `agent`,
`agent_tool` and `compile_agent_tool` are the design engine's LLM and the tool definition it
is given, not schema.org's person; `candidate` is a candidate *price* and `candidate_weeks` a
duration; `members` are the units in a stratum; `parents` is `pathlib`'s keyword in
`mkdir(parents=True)`; `url` is where a guardrail value's citation points; `weight_c` and
`weight_t` are the estimator's arm weights. A twelfth appearing turns `O5` or `O10` red, and
the fix is a conversation — never an addition made in the same commit as the name.

**Each entry is keyed by the *pair* — the name here and the name there — and that was a
finding too.** It was keyed on the bare identifier until oversight level 2 asked what that
excuses: an entry for `members` would have pre-approved any future `members` anywhere in the
package, including one that really is a collection of people, and `O12` would have stayed
green because the name still matched something. `O12` refuses an explanation that has outlived
the collision it explained, because an unused entry is a name pre-approved for whoever adds it
next.

---

## 5 · The seven mutations, and the six checks that cannot have one

Each mutation is written as a behaviour change in domain terms and names its check in advance.

| planted in | breaks | refused by |
|---|---|---|
| `core/decision.py` | the key learns who is buying — an optional `customer_id`, defaulted, breaking no caller | `O1` |
| `core/guardrails/certificate.py` | the certificate that reaches a shelf remembers the loyalty tier — planted on the one type that is **not** a dataclass | `O2` |
| `core/decision.py` | a second key rides alongside the first: a new *type*, no existing field touched | `O3` |
| `core/decision.py` | **the same second key, named `_VisitContext`** | `O3` |
| `core/decision.py` | the key stops being frozen and slotted, keeps all four fields, and anything can be stapled to it afterwards | `O9` |
| `core/guardrails/certificate.py` | the actuator is told who is buying — a `customer` **parameter**, which no field-set comparison can see | `O5` |
| `contracts/policies/ladder_policy@v1.yaml` | a decision becomes idempotent per customer. **No Python changes at all** | `O10` |

Two of them earn their checks. A parameter is not a field and a contract is not Python; every
check built on comparing field sets is blind to both by construction.

**And the fourth exists because the third survived a rename.** `unlisted()` skipped any class
whose name begins with `_`, inherited from the version of the rule that lived in
`tests/core/test_decision_key.py` where it read as ordinary hygiene — a private helper is not
on the decision path, so why write it down. What it did was leave one spelling that walks
straight past the guard while `O3`'s printed question said *every* type. Oversight level 2
renamed the class this table's third row plants, and watched it survive. The exemption is gone,
the estimator's three private types are written down like everything else, and the underscored
break is planted rather than argued about.

**Six checks have no mutation and cannot have one**, and the reason is the same in each case:
breaking them means editing the detector or the eval rather than the system, and a planter that
may edit the detector is the independence gone. That is no longer a convention either —
`ledger.no-mutation-edits-the-detector` refuses a mutation whose `file:` is under `ops/` or
`corpus/`. The six are armed instead by `tests/evals/test_oversight_instrument.py`, which
breaks each of them on a deliberately broken arrangement — a scan that lost `__slots__`, a
vocabulary whose words are ours after all, an explanation that explains nothing — and requires
the red. That is the arrangement `tests/evals/test_ledger.py` already has for `gate-proof`
itself.

---

## 6 · What this does not prove

* **That a name neither vocabulary publishes would be recognised.** `O4` and `O5` read names,
  and they can only read the 317 somebody else wrote down. What does not depend on any list is
  `O2`, and that is deliberate: the guard is the closed field set, and the name-reading checks
  are there to bound it rather than to be it.
* **That a field spelled without word boundaries would be matched.** `customerid` is one token
  and `O4` would not see it; `customer_id` is two and it would. The boundary rule is what stops
  a three-letter Presidio entity finding itself inside unrelated words, and its cost is stated
  here rather than discovered later.
* **That no person appears anywhere in the data this system reads.** The claim is about what a
  decision is *addressed by*. What a POS line contains is bronze's business, and bronze carries
  whatever the source sends.
* **That a person could not be re-identified by joining store, SKU and time outside this
  system.** Claim 7 is that no decision *targets* a person. It is not a statement about what
  somebody else could infer from an aggregate, and it would be dishonest to let it read as one.
* **That the eleven explained collisions are the only ones that will ever be innocent.** Each
  new overlap is a conversation.
* **That the mutation set is complete.** Seven breaks are the breaks we thought of — and one
  of the seven exists only because a reviewer thought of a spelling we had not. A gate can be
  perfect against all of them and still have a hole nobody imagined — the same honest limit the
  six adversarial worlds carry for claim 2.
