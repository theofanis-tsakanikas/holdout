# The legal posture

**Everything in this file was checked on 2026-08-27.** Every URL below was fetched and read
on that date. Where something could not be verified it is in [Not verified](#not-verified),
by name, with what was searched for — and it is **not** encoded anywhere in `contracts/`.

This document exists because of one line in the doctrine: **nothing is invented**. A
guardrail is where an invented number does the most damage, because a figure in
`contracts/guardrails/` is the last thing between a model and a shelf. So a numeric `value`
in a guardrail contract requires a `source`, `value` without `source` is a build failure,
and the source must declare which of exactly two kinds it is:

| kind | means | requires |
|---|---|---|
| `legal_instrument` | a provision that was read at its source | instrument · article · URL · `verified_on` |
| `scenario_assumption` | a stated position of the synthetic scenario | a note saying what is assumed and why · `verified_on` |

There is no third kind where a number simply appears. `make contracts` refuses a `value`
with no `source` at any nesting depth, and a test asserts that no `scenario_assumption`
carries an instrument, an article or a URL — the failure mode being an assumption dressed
as a citation.

---

## The one provision the architecture rests on

**Perishable food is outside the prior-price rule in Greece.** That is the whole reason the
fresh-markdown path is allowed to actuate itself.

Article 6a of Directive 98/6/EC requires that any announcement of a price reduction state
the *prior price* — the lowest price the trader applied over at least the 30 days before
the reduction. If that applied to expiring fresh, then every automatic markdown would be an
announcement carrying a 30-day lowest price, the ladder would have to reason about its own
price history before every step, and "markdown on expiring fresh actuates automatically"
would be false.

Article 6a(3) lets Member States write different rules for goods liable to deteriorate or
expire rapidly. The Commission's guidance says the derogation may go as far as a **complete
exemption**. Greece took it, and the exemption survives every subsequent amendment,
including the one that moved the rule into a different statute.

> **Article 6a(3), Directive 98/6/EC** — "Member States may provide for different rules for
> goods which are liable to deteriorate or expire rapidly."
> [EUR-Lex, consolidated 28.05.2022](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:01998L0006-20220528)

> **Commission Notice 2021/C 526/02, §4.1** — "Such rules may even consist of completely
> exempting such goods from the scope of Article 6a … Examples of goods liable to
> deteriorate or expire rapidly are fresh food and drinks with short expiry time limits."
> [EUR-Lex, OJ C 526/130, 29.12.2021](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:52021XC1229(06))

> **άρθρο 9ι παρ. 2 ν. 2251/1994**, as inserted by ν. 5111/2024 — «Η παρ. 1 δεν εφαρμόζεται
> για νωπά και ευαλλοίωτα γεωργικά προϊόντα και τρόφιμα τα οποία … ενδέχεται να καταστούν
> ακατάλληλα προς πώληση εντός τριάντα (30) ημερών …, ιδίως όσα περιλαμβάνονται στο
> Παράρτημα Ι του άρθρου 17 του ν. 4492/2017 (Α΄ 156).»
> [ΦΕΚ Α΄ 76/24.05.2024](https://kataggelies.mindev.gov.gr/wp-content/uploads/%CE%9D.5111_2024%CE%9176.pdf)

Two consequences the system has to encode rather than remember:

1. **Membership of the exemption is a product attribute, not an inference.** Whether a SKU
   falls inside Παράρτημα Ι του ν. 4492/2017 is resolved from the product master as of the
   decision. Deriving it from an observed shelf life would be inventing an expiry rule,
   which doctrine rule 3 forbids by name.
2. **The exemption escapes Article 6a and nothing else.** The unfair-commercial-practices
   provisions still apply, and ΔΙ.Ε.Π.Π.Υ. άρθρο 78 παρ. 4 requires the retailer to be able
   to *prove*, on inspection, that the original price printed on the label was really
   applied. That is the legal reason the **electronic shelf label acknowledgement is a
   first-class source in this system rather than a log**: it is the only evidence that a
   price reached the shelf.

---

## Verified — the prior-price rule

Encoded in `contracts/guardrails/prior_price.yaml` as four effective windows.

### Union law

| instrument | article | what it says | source |
|---|---|---|---|
| Directive 98/6/EC | Art. 1, 2, 3, 4 | selling price and unit price must be indicated, unambiguous, easily identifiable and clearly legible | [EUR-Lex consolidated](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:01998L0006-20220528) |
| Directive (EU) 2019/2161 (Omnibus), OJ L 328/7, 18.12.2019 | **Art. 2** | the amending article: inserts Art. 6a into 98/6/EC and replaces its Art. 8 on penalties | [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019L2161) |
| Directive 98/6/EC | **Art. 6a(1)–(2)** | an announced reduction must state the prior price; the prior price is the **lowest** price applied over **not shorter than 30 days** before | [EUR-Lex consolidated](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:01998L0006-20220528) |
| Directive 98/6/EC | **Art. 6a(3)** | Member States may set different rules for goods liable to deteriorate or expire rapidly | as above |
| Directive 98/6/EC | Art. 6a(5) | for progressive reductions, the prior price may be the one before the first reduction | as above |
| Commission Notice **2021/C 526/02**, OJ C 526/130, 29.12.2021 | §4.1, §4.3 | the perishable derogation may be a complete exemption; §5 applies only to *uninterrupted* progressive reductions and "shall be interpreted narrowly" | [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:52021XC1229(06)) |
| **CJEU C-330/23**, 26.09.2024, *Verbraucherzentrale Baden-Württemberg v Aldi Süd* | operative part | a reduction announced **as a percentage**, or as any promotional claim highlighting how advantageous the price is, must be computed **from the prior price** | [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:62023CJ0330) |

> **A correction worth recording.** The guidance notice is **2021/C 526/02** (CELEX
> 52021XC1229(06)), not 2021/C 526/01. Cite `curia.europa.eu` for C-330/23 and the link
> dies; the EUR-Lex CELEX link works.

### Greek transposition — four instruments, and the fourth moved the rule

This is the part the project's own `CLAUDE.md` understated. The rule did not merely change
its numbers; the **fourth amendment moved it into a different statute and repealed the old
provision outright**. A markdown announced in March 2024 is judged, permanently, by ν.
4177/2013 άρθρο 15 παρ. 2α — a provision that no longer exists. An implementation that
always reads "the current rule" gets that decision wrong and produces a confident answer
while doing so.

| in force from | instrument | what changed |
|---|---|---|
| **20.05.2022** | **ν. 4933/2022 άρθρο 3** (ΦΕΚ Α΄ 99/20.05.2022) — inserts παρ. 2α στο άρθρο 15 ν. 4177/2013. [PDF](https://kataggelies.mindev.gov.gr/wp-content/uploads/%CE%9D.4933_2022%CE%9199.pdf) | first transposition of Art. 6a; 30-day lookback, 10 days for new products; **no** perishable derogation |
| **02.09.2022** | **ν. 4965/2022 άρθρο 6** (ΦΕΚ Α΄ 162/02.09.2022) — adds παρ. 2β. [PDF](https://www.sate.gr/data_source/2022%CE%A0%CE%A1%CE%A9%CE%98-%CE%A6%CE%95%CE%9A162%CE%91.pdf) | **the perishable exemption is taken up** |
| **03.04.2023** | **ν. 5039/2023 άρθρο 12** (ΦΕΚ Α΄ 83/03.04.2023). [PDF](https://www.elinyae.gr/sites/default/files/2023-04/83%CE%91_2023.pdf) | παρ. 2α replaced: fixed 30 days; for a newer product, the period it has been on the market |
| **24.05.2024** | **ν. 5111/2024 άρθρα 3 και 43** (ΦΕΚ Α΄ 76/24.05.2024). [PDF](https://kataggelies.mindev.gov.gr/wp-content/uploads/%CE%9D.5111_2024%CE%9176.pdf) | **the rule moves to άρθρο 9ι ν. 2251/1994**; άρθρο 43 περ. α) repeals παρ. 2α and 2β of άρθρο 15 **and παρ. 2 of άρθρο 21** ν. 4177/2013; **progressive reductions now look back 60 days** |

Current Greek text, verbatim from ΦΕΚ Α΄ 76/2024, **άρθρο 9ι παρ. 1 ν. 2251/1994**:

> «Σε κάθε ανακοίνωση περί μείωσης τιμής υποδεικνύεται η προγενέστερη τιμή που εφάρμοζε ο
> προμηθευτής … Ως προγενέστερη τιμή νοείται η **χαμηλότερη τιμή** που εφάρμοσε ο
> προμηθευτής κατά τη διάρκεια του χρονικού διαστήματος των **τριάντα (30) ημερών** πριν
> από την εφαρμογή της μείωσης … Αν η τιμή μειώνεται προοδευτικά κατά τη διάρκεια των
> **εξήντα (60) ημερών** … ως προγενέστερη τιμή νοείται η τιμή που ίσχυε πριν από την
> εφαρμογή της πρώτης από τις διαδοχικές μειώσεις τιμών.»

The 60-day progressive window is wider than the 30-day general rule and wider than the
Commission guidance's framing. It matters here directly: a ladder that steps repeatedly
cannot reset its own reference by stepping again.

### Supporting instruments

| instrument | article | why it is in the contract |
|---|---|---|
| **ν. 4492/2017**, Παράρτημα Ι (ΦΕΚ Α΄ 156/18.10.2017). [PDF](https://www.elinyae.gr/sites/default/files/2019-07/156a_2017.1508398011625.pdf) | άρθρο 17, Παράρτημα Ι | the list the perishable exemption points to — tomatoes, onions, brassicas, lettuce, carrots, cucumbers, peppers, potatoes, mushrooms, pork/lamb/goat/rabbit, fresh and pasteurised milk, fish, shell eggs, feta and cheeses, yoghurt, charcuterie |
| **ΥΑ 19138/2025**, Κώδικας Δεοντολογίας (ΦΕΚ Β΄ 1140/12.03.2025). [PDF](https://www.greekecommerce.gr/wp-content/uploads/2025/03/%CE%A6%CE%95%CE%9A-1140-12032025-%CE%9D%CE%95%CE%9F%CE%A3-%CE%9A%CE%A9%CE%94%CE%99%CE%9A%CE%91%CE%A3-%CE%94%CE%95%CE%9F%CE%9D%CE%A4%CE%9F%CE%9B%CE%9F%CE%93%CE%99%CE%91%CE%A3.pdf) | §3.3.3, §§78–80 | confirms the exemption in its current form; confirms the UCPD still applies to exempt goods; penalties €5,000–1,500,000, with a ceiling of €3,000,000 where **more than one** penalty decision was issued against the trader in the preceding five years. Repeals ΥΑ 66877/2024 (Β΄ 5002) |
| **ΥΑ 91354/2017**, Κανόνες ΔΙ.Ε.Π.Π.Υ. (ΦΕΚ Β΄ 2983/30.08.2017). [PDF](https://www.mindev.gov.gr/wp-content/uploads/2021/05/%CE%A5%CE%9191354_2017_%CE%A6%CE%95%CE%9A-%CE%92-2983.pdf) | **άρθρο 78 παρ. 4** | the retailer must be able to prove the displayed original price was really applied — the legal reason the ESL acknowledgement is a source and not a log |

> **A date caveat.** The ΔΙ.Ε.Π.Π.Υ. gazette's own page footer reads «Τεύχος Β΄ 2983/30.08.2017».
> At least one index page gives 30.07.2017. The gazette is trusted here.

### One EU-wide fact worth knowing

Commission implementation report **COM(2024) 258 final/2**
([PDF](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:52024DC0258R(01))),
§7 — running prose, not a table, so read it there rather than trusting this summary. Member
States fall into **four** groups, not two:

| | |
|---|---|
| Art. 6a **does not apply** to perishables | Austria, Belgium, Czechia, Finland, France, Germany, **Greece**, Hungary, Italy, Latvia, Lithuania, Spain, Sweden |
| Art. 6a applies **with a reduced reference period** | Bulgaria (7 days), Romania (10), Denmark (14), Portugal (15) |
| Art. 6a applies **in full** | Cyprus, Estonia, Malta, the Netherlands, Poland, Slovenia |
| **no derogation taken** | Croatia, Ireland, Luxembourg |

**The Greek answer is not portable.** A chain operating across the Union cannot carry one
prior-price rule — and it cannot carry one *binary* either, because a reduced reference
period is neither exemption nor full application. The envelope in this repository is written
for one Member State and says so.

**The report gives no Greek national definition of "perishable".** If the guardrail ever
needs an operative definition — and the decision path does need one, per SKU, per decision —
it must come from Greek law (Παράρτημα Ι του άρθρου 17 ν. 4492/2017, which άρθρο 9ι παρ. 2
points at with «ιδίως», i.e. indicatively and not exhaustively), never from that report.

---

## A correction, recorded rather than quietly fixed

**The per-unit framing belongs to 2022, not 2021.** An earlier version of
`contracts/guardrails/regulated_basket.yaml` carried, in its 2021 window:

```yaml
value: per_unit_vs_seller_margin_before_2020_09_01
source: {kind: legal_instrument, instrument: "ν. 4818/2021 …", article: "άρθρο 58 παρ. 1"}
```

**«ανά μονάδα» does not occur anywhere in ν. 4818/2021.** The 2021 provision says only that
the gross margin may not become «μεγαλύτερο του αντίστοιχου περιθωρίου προ της 1ης
Σεπτεμβρίου 2020»; it states a benchmark and no basis. The per-unit basis first enters with **ν. 4903/2022 άρθρο
50**, where the text says it twice in one sentence. The contract had imported the successor's
arithmetic into the predecessor's window and stamped the predecessor's citation on it.

Nothing in this repository could have caught that. The instrument was real, the article
existed, the URL resolved, the schema validated, the provenance walk passed. **A citation
that is real but says something other than what the value claims is mechanically
indistinguishable from one that says what it claims.** The only defences are a quote long
enough to be checked and a reader who checks it — which is why the 2021 quote now carries the
two clauses the earlier one elided:

- the measure is **conditional on the COVID-19 emergency** and self-limited to 31.12.2021
  («Εφόσον, υφίσταται άμεσος κίνδυνος διασποράς του κορωνοϊού COVID-19 και πάντως όχι πέραν
  της 31ης.12.2021»), and
- its scope is **wider than nutrition** — «την υγεία, τη διατροφή, τη διαβίωση, **τη
  μετακίνηση και την ασφάλεια**».

Each elision made the overreach harder to see. `cap_basis` and `cap_benchmark` are now
separate rules in every window, because they are separately sourced and they moved at
different times; the 2021 basis is `unspecified_in_the_instrument`, a scenario assumption
that names the law only in order to disown it.

While correcting this, three citations of the same class were found and fixed: a claim about
Greek law sourced to a Directive article that speaks only about what Member States *may* do;
two "the provision continued unchanged" claims sourced to the instrument that created them,
now carrying a note saying the continuation is an inference; and four paraphrases sitting in
`quote` fields, now moved to `note`.

---

## Verified — the gross-margin cap

Encoded in `contracts/guardrails/regulated_basket.yaml` as six effective windows, of which
three state that **no cap is encoded** and say why.

`CLAUDE.md` says the Greek cap "changed twice in six months". The real history is a better
argument than that: between 2021 and 2026 the cap changed **shape** twice.

| in force | instrument | unit of comparison | benchmark |
|---|---|---|---|
| 18.07.2021 → | **ν. 4818/2021 άρθρο 58** (ΦΕΚ Α΄ 124/18.07.2021). [PDF](https://www.sate.gr/data_source/2021%CE%A0%CE%A1%CE%A9%CE%98-%CE%A6%CE%95%CE%9A124%CE%91.pdf) | gross margin **per unit** | the seller's own margin **before 01.09.2020** |
| 05.03.2022 → 30.06.2022 | **ν. 4903/2022 άρθρο 50** (ΦΕΚ Α΄ 46/05.03.2022). [PDF](https://www.sate.gr/data_source/2022%CE%A0%CE%A1%CE%A9%CE%98-%CE%A6%CE%95%CE%9A46%CE%91.pdf) | gross margin **per unit** | the seller's own margin **before 01.09.2021** |
| **11.03.2026 → 30.06.2026** | **ΠΝΠ της 11.3.2026** (ΦΕΚ Α΄ 37/11.03.2026), ratified by **ν. 5289/2026** (ΦΕΚ Α΄ 45/20.03.2026), **άρθρο δεύτερο**. [PDF](https://www.dsanet.gr/Epikairothta/Nomothesia/45.PDF) | gross margin **per product code**, as a percentage | the **2025 full-year average** |

> **άρθρο δεύτερο, ΠΝΠ 11.3.2026** — «Από την έναρξη ισχύος του παρόντος και έως την 30ή
> Ιουνίου 2026 απαγορεύεται η αποκόμιση μεικτού περιθωρίου κέρδους από την πώληση
> οποιουδήποτε προϊόντος, που είναι απαραίτητο για τη διατροφή και τη διαβίωση του
> καταναλωτή, εφόσον το μεικτό περιθώριο κέρδους, υπολογιζόμενο **ανά κωδικό προϊόντος**,
> υπερβαίνει τον **μέσο όρο** του αντίστοιχου μεικτού περιθωρίου κέρδους **του έτους 2025**.»

**Why this is the strongest argument for effective windows in the whole project.** The
arithmetic is not the same arithmetic. A decision taken in April 2022 is judged per unit
against a point in time; one taken in April 2026 is judged per SKU against an annual
average. There is no single "current cap" field that could hold both, and code that had
hard-coded either would keep returning a number under the other regime — a plausible
number, computed the wrong way, with nothing red anywhere.

### How the 2026 cap is enforced, and where the enforcement is stricter than the rule

Read this before taking the `per_product_code` cap as implemented compliance. **It is not.**

The measure compares an **aggregate** — the gross margin of a product code — against the
2025 full-year average. A single pricing decision does not have that aggregate in front of
it: it needs the code's realised margin for the period, which is a gold table and not an
argument to a pure function. `src/holdout/core/guardrails/` therefore bounds **each
decision's own margin** against the supplied benchmark.

| basis | what the instrument says | what this repository computes |
|---|---|---|
| `per_unit` (2022) | the margin on a unit against the margin on a unit before a date | the same thing. Exact |
| `per_product_code` (2026) | an aggregate over a code against a full-year average | the margin on **this decision**, against the benchmark. **Stricter** — it refuses prices the measure would allow once averaged down |
| `unspecified_in_the_instrument` (2021) | nothing; ν. 4818/2021 does not say | nothing. The decision is **refused** with `MARGIN_CAP_BASIS_UNEVALUABLE` rather than evaluated with a neighbouring regime's arithmetic |

Erring toward refusal is the direction this system is built to err in, and the choice is
recorded in three places — here, in `contracts/guardrails/regulated_basket.yaml` beside the
value, and in the rule's own docstring — because a reader of any one of them would
otherwise take it for compliance.

**A note on what is currently reachable.** `floor`, `max_delta` and `frozen_categories` all
open on 2025-01-01, so `envelope_as_of` cannot build an envelope for any date before that.
The 2021 and 2022 windows of this guardrail are therefore not reachable through the
contract path today: `MARGIN_CAP_BASIS_UNEVALUABLE` and the `per_unit` basis are live code
guarding a **future** instrument that again states no basis, not a demonstrated property of
the 2021 window. They are exercised in the tests against hand-built envelopes.

Also verified in the same instrument: **άρθρο τρίτο** — fines of €5,000 to €5,000,000,
calibrated on firm size, gravity, duration and economic benefit, **doubled on repetition**,
up to €50,000 for obstruction, enforced by the Ανεξάρτητη Αρχή Ελέγχου της Αγοράς και
Προστασίας του Καταναλωτή. And **άρθρο τέταρτο** — the scope is fixed by ministerial
decision, and the measure may be **ended early** by ministerial decision. There is no power
to extend it.

---

## Scenario assumptions — stated, not law

Everything in this section is a position of the **synthetic scenario**. None of it is a
claim about what any law requires, and none of it carries an instrument, an article or a
URL in `contracts/`. A test enforces that last point.

| where | what is assumed | why it is not law |
|---|---|---|
| `guardrails/floor.yaml` | minimum gross margin **0%** — sell at cost, never below | whether and how below-cost selling is restricted was **not verified** for this project; no legal minimum is encoded |
| `guardrails/floor.yaml` | minimum absolute price **€0.05** | an operational bound: a zero or negative price is a data defect, not a decision |
| `guardrails/floor.yaml` | a cost older than **24 hours** is stale | the scenario's ERP publishes daily; a stale cost puts the floor in the wrong place and every price above it still passes every other check |
| `guardrails/floor.yaml` | a refusal is the correct output when no legal price sells the item | doctrine, not statute |
| `guardrails/max_delta.yaml` | markdown depth **≤ 70%**; **≤ 4** changes per SKU per store per day; base price **+10% / −20%** per pricing week | commercial and operational bounds of the scenario. The depth and the change budget are set to the ladder's deepest step and step count, so the envelope binds the policy rather than trailing it |
| `guardrails/frozen_categories.yaml` | tobacco, spirits, infant formula, pharmacy — and fresh fish from 01.11.2025 | each of these is subject to price or marketing rules in real markets and **none of those rules was verified here**. They are frozen because the scenario declines to automate them, not because an instrument was read |
| `guardrails/regulated_basket.yaml` | the basket's categories are `dairy`, `bakery`, `poultry` | the real scope is fixed by a ministerial decision under άρθρο τέταρτο, reported to name 63 categories. **That decision was not obtained**, so its list is not reproduced. *Restated 2026-08-27: it has since been read, and its 63 categories are transcribed in `corpus/real/`. The contract still names three, still as an assumption — see item 6 under "Not verified" and the deferred entry in `docs/DECISIONS.md`* |
| `guardrails/regulated_basket.yaml` | no cap in force 01.01.2022–05.03.2022, 01.07.2022–11.03.2026, and from 01.07.2026 | see [Not verified](#not-verified). These windows record what this repository verified, **not** a claim that no cap existed |
| `policies/ladder_policy@v1.yaml` | ladder depths 20 / 35 / 50 / 70% at 24 / 12 / 6 / 3 hours to expiry | shaped to resemble publicly described fresh-markdown practice; **no chain's actual schedule was obtained** and none is claimed |

---

## Not verified

Named here so that nothing in this list can be quietly promoted to a fact later. **None of
it is encoded in `contracts/`.**

### The gross-margin cap, 2022–2026

1. **Any bridge into 2022.** Only half of this is unverified, and an earlier version of this
   file understated its own evidence. The **end date is on the face of the text already
   quoted** — «πάντως όχι πέραν της 31ης.12.2021» — so the window boundary is sourced and is
   now encoded as a `cap_expires_on` rule with that citation. What remains unverified is
   whether anything bridged 01.01.2022 → 05.03.2022; **ν. 4876/2021** is a candidate that was
   never opened. Encoded as *no cap* over that interval, labelled as a declared hole.
2. **The 2023–2025 chain.** ν. 5045/2023 άρθρο 54 (reported ΦΕΚ Α΄ 136/29.07.2023) and its
   reported extensions by ν. 5079/2023 άρθρο 57, ν. 5116/2024 άρθρο 59 and a 2025
   instrument (reported as ν. 5194/2025 άρθρο 51). These were retrieved only through an
   `et.gr` download API that **301-redirects to a bare IP address whose TLS certificate
   does not match the host**, so certificate verification had to be disabled. The content
   was self-consistent, but the transport was not authenticated, and that is not good enough
   for a figure that would go into a guardrail. Encoded as *no cap*, 01.07.2022 →
   11.03.2026.
3. **The ministerial decision fixing the "before 31.12.2021" reference window** under ν.
   5045/2023 §54(7). Never found. Without it, "the margin before 31.12.2021" is not a
   computable quantity, which is a second reason nothing from that regime is encoded.
4. **A conflicting account of the origin.** One secondary source gives the chain as ν.
   4876/2021 άρθρο 64 → ν. 4903/2022 → ν. 5045/2023 → ν. 5194/2025, which contradicts the
   primary finding that ν. 4818/2021 άρθρο 58 is the origin. Unresolved.
5. **Whether the cap is in force today, 2026-08-27.** No instrument was found extending the
   emergency measure past 30.06.2026, and none confirming it lapsed. The measure's own text
   supports expiry — a hard end date, a power to end it early, no power to extend. Press
   reporting from June 2026 points both ways and several of those pages returned HTTP 403.
   Encoded as *no cap* from 01.07.2026, with the uncertainty on the record.
6. **ΥΑ 21330/2026** (reported ΦΕΚ Β΄ 1411/12.03.2026), which fixes the categories in scope
   for the 2026 cap. Never opened. The reported 63 categories, the reported margin formula
   `(selling price − average cost of goods sold) / selling price` and the reported 2025
   reference period are **secondary only** and none of them is encoded.

   > **Restated 2026-08-27.** It has now been opened — at a legal-database reproduction,
   > which is not the Gazette, and the distinction is kept. The decision's text was read
   > directly: **άρθρο 6** carries the table of 63 categories, transcribed verbatim into
   > `corpus/real/data/greek-regulated-basket-2026.csv`; **άρθρο 4 παρ. 4** defines
   > `ΠΜΚ = (Τιμή Πώλησης − Μέσο Κόστος Πωληθέντων) / Τιμή Πώλησης`, confirming the reported
   > formula and, importantly, that the margin is a fraction of the **selling price** rather
   > than a mark-up on cost; **άρθρο 4 παρ. 5** fixes the reference period as the last closed
   > financial year of 2025, or 01.01.2025–31.12.2025. The gazette reference ΦΕΚ Β΄ 1411/
   > 12.03.2026 is stated identically by taxheaven.gr, e-nomothesia.gr and nomotelia.gr, and
   > the category list agrees item for item with an independent prose enumeration in the
   > press (efsyn.gr, 13.03.2026).
   >
   > **Still none of it is encoded in `contracts/`.** The list lives in `corpus/real/`, which
   > is the independent corpus claim 1 attacks the gates *from*, and a corpus is not a
   > contract. Moving it into `regulated_basket.yaml` opens a new effective window and a
   > restatement chain; `docs/DECISIONS.md` records that as deferred, with its unlock
   > condition. What changes today is only this: the decision is no longer unread.

### Other

7. **«Καλάθι του νοικοκυριού».** The scheme's legal basis — **ν. 4986/2022 άρθρο 87** (ΦΕΚ
   Α΄ 204/28.10.2022) — and its extensions through 31.12.2024 were traced, but every 2025
   extension, and the instrument that fixed 31.10.2025 as its final expiry, are **press
   only**. The implementing decision ΥΑ 104093/2022 (Β΄ 5580/31.10.2022) with its category
   list was never opened. **Nothing about the household basket is encoded in `contracts/`,**
   and note that the original scheme explicitly left prices free — §3 hinged it onto the
   margin cap rather than setting prices itself.
8. **Below-cost selling.** Whether and how it is restricted in Greece was not researched.
   The floor guardrail therefore encodes a *commercial* minimum margin of 0% as a scenario
   assumption and no legal minimum at all.
9. **Tobacco, alcohol, infant formula and pharmacy pricing rules.** Real constraints exist
   in these categories; none was verified. They are frozen categories in the scenario for
   that reason, which is the honest way to decline to model something.
10. **ν. 5255/2025** (reported ΦΕΚ Α΄ 219/28.11.2025), creating the Ανεξάρτητη Αρχή Ελέγχου
    της Αγοράς και Προστασίας του Καταναλωτή. The gazette was never opened; the authority's
    existence is nonetheless verified indirectly, because the 2026 ΠΝΠ names it at primary
    source.
11. **A consolidated text of άρθρο 9ι ν. 2251/1994.** Every amending instrument was read in
    the gazette, but no free authoritative consolidation was available to confirm that
    nothing further changed after 24.05.2024. Searches for 2025–2026 amendments returned
    nothing, and the March 2025 Code of Conduct describes άρθρο 9ι in the form encoded here,
    which corroborates it to that date. Note that `lawspot.gr` serves the **2013 original**
    of άρθρο 15 ν. 4177/2013 and is wrong as a source for this.
12. **`sate.gr` refuses a bare fetcher.** Three of the Greek citations above — ν. 4818/2021,
    ν. 4903/2022 and ν. 4965/2022 — are hosted there, and the host returns **HTTP 403** to a
    default programmatic user-agent while serving the same URL normally to a browser. The
    documents were read; the URLs will look dead to anyone checking them with `curl`. This
    matters for publication and is a second reason to move to `search.et.gr` permalinks.
13. **Stable Εθνικό Τυπογραφείο permalinks.** No working `et.gr` direct-download URL could
    be constructed. Every Greek citation above therefore points at a mirror that carries the
    correct ΦΕΚ footer and pagination — `mindev.gov.gr`, `elinyae.gr`, `sate.gr`,
    `dsanet.gr`, `greekecommerce.gr`. **Before this repository is published, each should be
    re-opened through <https://search.et.gr/el/> and the permalink recorded here.**

---

## How this is kept honest

* `make contracts` fails when any `value` has no `source`, at any nesting depth — the walk
  is independent of the JSON Schema precisely so that a schema written today cannot be
  widened tomorrow into a hole.
* A `legal_instrument` source must carry an instrument, an article, an `https` URL and a
  `verified_on` date, **and either a verbatim `quote` or a `note` accounting for its
  absence**, or the build fails.
* **`quote` is verbatim text and nothing else.** A summary, an extract, a rubric gloss or an
  English paraphrase goes in `note`, labelled as such. The quote is the only part of a
  citation a reviewer can check without opening the gazette, so a quote that has been
  helpfully tidied is worse than no quote at all — see the correction below.
* **A citation that supports a continuation rather than a creation says so in its `note`.**
  "This provision still stood in this window" is an inference from no amending instrument
  having been found, not something any article states.
* A `scenario_assumption` must carry a note that says what is assumed, and a test asserts it
  carries **no** instrument, article or URL.
* Every guardrail's windows must be **contiguous and non-overlapping**. A period during
  which a rule did not apply is written as a window that says so, with its own source,
  because an absent window and a lapsed rule look identical on disk and only one of them is
  a fact.
* **Verification dates age.** Every `verified_on` in this repository reads 2026-08-27. A
  citation is a claim about a moment; treat anything more than a few months old as
  unchecked, and re-open the gazette rather than trusting this file.
