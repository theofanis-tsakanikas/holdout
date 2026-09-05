# Findings

A finding is something a review said is wrong. This file is where one lives while it is open,
and `make findings` is what stops it leaving without being closed.

**Read this paragraph before trusting anything below it.** A representation is not the thing, and
every mechanism in this project produces representations. `make figures` is a representation of
coverage; `make language` matches a character range and concludes about language; this file is a
representation of findings. It will fail the same way they can, and the failure will look like a
green run. What it buys is not truth — it is that **silence stops being free**.

---

## Why this file exists

Every mechanism this repository had was aimed at a **claim**, a **gate** or a **deferral**. An open
review finding is none of the three, so it had nowhere to fall out of, and two of them fell.

**On 2026-08-27 oversight level 2 recorded three blocking findings against claim 1.** T000 closed
the first two and the type-level half of the third. The legal half of the third — a 2008–2020
industry median described as the 2025 benchmark, and an equivalence read into an article that does
not contain it — was never closed and was never deferred. It simply stopped being anywhere. **Four
days, twenty-one commits, and neither `make expiry` nor the phase-1 integration session could see
it**: not a deferral, so the first had nothing to read; not named in `CLAUDE.md`, so the second had
nothing to check against.

**And the review that found that lost one of its own.** `docs/reviews/phase-1.md` §4 —
`pricing/selection.py`, the one core module no eval reaches and no mutation targets — was recorded
in a document whose closing table assigns every other section to a branch, and assigned to none.
One day, in a nine-row table written for exactly that purpose.

Two findings, two documents, two different ways of losing them. Neither was caught by anything.

---

## What the gate checks

**A finding anchors to a line that already exists.** Each `*Site:*` names a file and quotes a
fragment that must occur in it **exactly once**. Zero means the line moved or was fixed — in which
case the finding is either stale or closed, and either way somebody has to say which. Two means the
anchor is ambiguous and proves nothing about which line was meant. It is
`ledger.every-anchor-is-aimed-at-one-place` with a new population, and that check is not a guess:
it is what refused a hand-applied mutation 16 during `ops/claims-are-required`.

**A finding with no site is refused.** Not badly filed — a finding whose consequence is recorded
nowhere, which is precisely what the legal one was for four days.

**A finding declares a disposition**, and `none — <reason>` is a disposition. What is refused is
saying nothing. An entry that names no branch, no task and no reason is **adrift**: it is reported
in its own count and it does not turn the gate red, because a finding nobody has scoped yet is a
real state and refusing it would only teach people not to file.

**Closure is a transition, not a verdict.** An entry closes on exactly three things: the anchored
line changing, a branch landing with the gate going red-to-green, or a named human saying so. Any
of them goes in a `*Closed:*` line with the date and what happened.

**And closure restates a site rather than releasing it.** A closed entry keeps being checked — on
the text that replaced the defect. Every site gets a `*Now:*` line carrying either that text, held
to the same exactly-once rule for as long as the entry exists, or `gone — <reason>` where nothing
replaced it. The original `*Site:*` stays beside it, per doctrine rule 4.

This is not tidiness. **A finding that stops being examined the moment somebody accounts for it is
a claim about the past that reads as a claim about the present**, and a fix reverted in November
would leave this file saying `closed` forever. It is the legal finding's own story one layer along:
two of its three parts were closed, and what made the third invisible was that nothing re-examines
a thing already accounted for. The first draft of this registry had exactly that property and the
reviewing session found it before the file landed.

The price is naming the replacement text, not only the transition — the price the `[M]` rule
already charges: a number is not published without the command that produces it, so a defect is not
recorded as fixed without the text that fixed it.

### `concurred` is not `closed`

**Two agents agreeing is not a check.** It is two representations agreeing, which buys nothing
about truth — and it is how one of these findings would have left the record a second time. On
2026-08-31 the reviewing session removed §4 from the author's list on the grounds that the two
sessions concurred; the builder session objected that this is the exact mechanism by which the
legal finding was lost, *not a decision to drop it, but two parties who held it agreeing it was
handled and nobody holding them to that.*

So `*Status:* concurred` is a state this file can carry, it prints in its own count, and it is
**counted as open**. If the two heaviest users of a register could retire an entry by agreeing,
the register would measure their agreement rather than the repository.

> *It was my finding, and that is exactly why I should not be the one deciding it needs no
> oversight.*
>
> *It was not my finding, and that is exactly why my agreement is worth less than it feels.*

Neither works alone. And the instance that produced them was caught inside an hour only because
one party happened to remember a rule it had stated that morning — which is not a defence, and is
this file's own blind spot rather than an argument that it does not have one.

### The anchor and doctrine rule 4, which interact

**An anchor detects drift and revert. It cannot detect *fixed*, and that is an interaction with
this repository's own convention rather than a shortcoming of anchors.**

Doctrine rule 4 says a correction never erases what was previously stated. So a fix here usually
*restates*: the new text goes in and the defective wording is kept beside it, quoted. The anchor is
on the defective wording — so it survives the fix, and the entry stays green while its subject is
already repaired. Closure is what records that, and closure is a transition rather than an anchor
vanishing, which is why nothing breaks.

**An anchor vanishing is therefore the unusual case, and it means the site was *rewritten* rather
than restated** — that is, the repository's own convention was not followed there. `MOVED` asking a
person is exactly right for that: it fires precisely where somebody should look.

*Both behaviours appeared within an hour of this file landing, on the same fix.*
`corpus/legal-claims-restated` restated three sites with the old wording quoted, and their anchors
held; it rewrote `PLAN.md`'s, and that anchor vanished and turned the gate red. Same branch, same
finding, two behaviours, decided by how each restatement was written. Neither session saw it at
design time. The answer was to **split** the entry — one anchor was answering for two defects with
different fixes and different landing dates — rather than to loosen the check, and the split
produced this file's first closure through the mechanism instead of around it.

### The count is printed and asserted by nobody

`tests/ops/test_findings.py` asserted `len(findings) == 2` until the split above turned it red on a
legitimate change. **A frozen count standing in for the property it was there to protect**, inside
the work about numbers standing in for things. The property — both founding entries filed open,
dated before any branch that touches them — is what the test asserts now. The count is printed by
`make findings` and claimed by nothing.

**The standing limit.** An anchor proves a line exists and still reads as expected. It cannot prove
it is the **right** line. A true but irrelevant anchor is a green that means nothing, and no
mechanism here can catch it — the same limit as a mutation planted against the detector, which this
repository closed by putting the detector out of reach rather than by testing the choice.

---

## Open
**The shell surface of `main_guard`, and whether parsing a command is the right basis at all** ·
found 2026-08-31 · by `holdout-e0` and oversight level 2 · *the git surface is closed; this half
is a decision the author has deliberately not taken yet*
The git-interface half is finished. `--attr-source` and `--config-env` were **missing** from
`_TAKES_A_VALUE` and each let a `git commit` past unseen; `--exec-path` was **present and should
not have been**, because its optional value must be attached with `=`. All three are settled
against `git help git` rather than against memory, and
`test_no_documented_option_lets_a_commit_past_the_guard` holds the file to git's behaviour over
every documented option, with **two** repositories.

*What is deliberately left open, and it is not an oversight.* **`cd` and `pushd` are not parsed at
all.** `cd <a checkout on main> && git commit`, from a session on a branch, is allowed — and the
commit **lands**, measured by counting rather than by reading a verdict. The mirror is refused
wrongly. `pushd` is a second spelling and `(cd X; git commit)`, `cd` through a variable and
`bash -c '…'` are the beginning of a third enumeration.

*Why no list is being added for them.* Three enumerations were shown incomplete by measurement in
one day — the target flags, the value-taking flags, and now the shell. **Adding two names to a
third list, on the day three lists were shown incomplete, is the move this whole sequence is an
argument against.**

*The exposure, measured rather than assumed, which is what makes deferring it a decision.* The
`main` ruleset is `enforcement=active` with **`bypass_actors: []`**, requiring `pull_request`,
`non_fast_forward`, and the checks `gate`, `secrets` and `claims-complete` — read from the API, not
quoted. So a commit reaching local `main` through any shell-surface hole **cannot reach `origin`**,
by anyone. The cost is a local mess recoverable with `git reset`; it cannot be a published one.
**The rule is enforced twice — imperfectly here, completely at the boundary that matters** — and
this hook's job on that surface is to catch the mistake early rather than to be the thing that
prevents it.

*The question, which is the author's and is not answered here:* **is parsing an arbitrary shell
command the right basis for the shell half**, given that three enumerations over it have each been
found incomplete, that the guard is a speed bump with a human behind it, and that the ruleset
already refuses the push? *Accept approximate, with the reason written down* and *no, and the
answer is not another list* both have evidence behind them.

*And the axis matters, because the obvious framing is wrong.* Classifying all nine defects two ways
— **surface** (git's interface / the shell) against **family** (redirects the commit / hides it) —
puts both families on **both** surfaces. So *targets are closeable, detection is not* does not hold:
`cd` is a redirect and it is open; `--attr-source` was a hide and it is closed. The line falls
between git's interface, which is documented and finite and has now been enumerated against, and
the shell, which is neither.

*Site:* `.claude/hooks/main_guard.py` :: `_SEPARATORS = {"&&", "||", ";", "|", "&", "(", ")", "{", "}"}`
*Disposition:* the author's, deferred with the exposure measured — the fix is not a list, and which
it should be is a design judgment with a person's name on it
*Status:* open

**`main_guard` is judged against something other than the command it refuses — twice** · found
2026-08-31 · by `holdout-e0` and oversight level 2, measured by both
**The hook is not changed here.** It enforces a rule its author reserved to himself, the harness
applies it whether a session consents or not, and editing it changes the guard before any review
sees it. This entry records the defects, the measurements and the design, so that none of it lives
only in a conversation — which is the failure that cost a branch earlier the same day.

*One sentence covers both:* **the guard is judged against something other than the command it is
refusing** — the wrong **directory** in the first, the wrong **text** in the second.

**Defect 1 — the directory.** `main()` reads `event["cwd"]`, the *session's* directory, and resolves
the branch there. `-C` is in `_TAKES_A_VALUE` and is used only to skip past its value when finding
the subcommand: the path is parsed and thrown away. Measured by feeding the hook crafted events:

    cwd on main, committing INTO a worktree on a branch     exit=2  REFUSED   (should allow)
    cwd on a branch, committing INTO the checkout on main   exit=0  ALLOWED   (should refuse)

The second is **the guard permitting exactly what it exists to prevent**, and the arrangement that
reaches it — a session in a worktree running `git -C` against the shared checkout — is the one
`CLAUDE.md`'s git rule requires when two sessions share a repository.

*Never exploited.* `main_guard` landed 2026-08-27 11:17 in `#7`. Seven commits on `main` carry no
`(#N)`: four predate the hook, and `a47c2a8`, `32f475e` and `d105334` went through PRs #15, #14 and
#1, verified against the API. **No direct commit to `main` has landed since the guard existed.**

*Interim discipline, closing the exposure by convention while the code is unchanged:* **no session
runs `git -C <the shared checkout>` from a worktree.** That is the only combination that reaches the
open direction.

**Defect 2 — the text, and it is two defects wearing one description.** Both refuse a command that
writes a file quoting a git command. They arrive by different routes:

    REFUSED  cat > note.md <<'EOF' … prose with an apostrophe AND a `&&` in the quoted text
    allowed  the same prose with no apostrophe
    allowed  prose quoting the command with no separator in it

The first needs **both** an apostrophe — to unbalance `shlex` and fall through to `_COARSE` — and a
shell operator inside the quoted text for `_COARSE` to match after. The docstring's own example,
*Don't run `git commit` here*, is the half-case that works, which is why its author believed it
closed.

The second route never touches `_COARSE`:

    REFUSED  bash <<'EOF'             … body is RUN      correct
    REFUSED  cat > runbook.md <<'EOF' … body is WRITTEN  wrong

Identical bodies. `_segments` splits on lines, the body line tokenises cleanly, `_is_git_commit`
returns true. **The two commands differ only in the consumer before `<<`** — so nothing about the
body can separate them, and the written-versus-executed distinction is not one option among several
but the only thing that carries it.

**The design, since it is the part that took the longest to reach.** Excise the heredoc body **only**
when the consumer is `cat` or `tee`, with no pipe onward, writing to a file or a redirect. Everything
else keeps its body matched. That is a **whitelist of two rather than a classification of all
consumers**: not *is this executed?*, which requires understanding the command, but *is this one of
the two forms that provably cannot execute?*, which is a string comparison. `cat <<'EOF' | bash`
fails closed because the pipe disqualifies it, without needing a downstream rule.

**And the accounting that the docstring must carry, because getting it wrong is how the hole opens.**
Two refusals happened today. **One was a false positive** — `cat > note.md <<'EOF'`, which the
whitelist fixes. **The other was a correct refusal that felt like one**: `python - <<'PYEOF'`, run
while measuring the first. Its body executes and can reach git through `os.system` or `subprocess`
with no line beginning with `git`, so refusing it is the guarantee holding.

> **A refusal recorded as a false positive is a refusal somebody later removes.** The next session
> meets `python <<EOF` refused, finds it listed as a known false positive, and widens the whitelist
> to include `python` — which opens exactly the hole the whitelist exists to leave closed. The
> complaint becomes a fix becomes the defect.

So `python`, `bash`, `sh` and anything not `cat` or `tee` are refused **deliberately**, and **the
workaround is the editor tool, not a wider list.** That sentence is the one that stops the next
repair — the same move as *never narrow this walk to match*: name the repair somebody will reach
for, and refuse it in advance.

**Five attacks, all blocking, with today's baseline measured so a rewrite has a starting point
rather than an assumption:**

| attack | required | today |
|---|---|---|
| `git -C <worktree on a branch> commit` | allow | REFUSED |
| `git -C <checkout on main> commit` from a branch session | refuse | **ALLOWED** |
| heredoc writing prose that quotes the command | allow | REFUSED |
| `cat > f <<'EOF'` whose body line begins with `git` | allow | REFUSED |
| `bash <<'EOF'` whose body commits | refuse | REFUSED |
| the two-line `git add -A` / `git commit` — a recorded miss | refuse | REFUSED |

*And the stop rule:* if the written case cannot be allowed while the executed case is refused,
**ship the directory fix alone and file the text half.** The directory fix is mechanical and has no
residual; the text half grew twice under examination. Half a fix to a guard is better than a whole
one that opens it, and this file records three instances today of a repair reintroducing what it was
repairing.

*It is the third instance in this one hook.* `CLAUDE.md` already records it biting the one-line
`&&` form and missing the two-line one. Neither the docstring nor `.claude/README.md` mentions
worktrees or heredocs — **a known miss with nowhere written down is how the first one survived long
enough to become three**, and both places take both new cases when the fix lands.

*And this entry's own disposition is a live instance of the state that gate was designed for.* It
names `ops/main-guard-judges-the-command`, which does not exist. Under the branch-state gate
designed and then refused earlier the same day, that would print **`nowhere`** — and printing it
would be **correct**: a branch proposed and not started is an honest absence, nothing anywhere
claims it landed, and the line beside it says why. The register is carrying a truthful `nowhere` on
the day the gate that would have reported it was filed, which is the argument for *printed, not
refused* arriving as an example rather than as a rule.

*Site:* `.claude/hooks/main_guard.py` :: `    branch = current_branch(Path(cwd) if isinstance(cwd, str) else Path.cwd())`
*Disposition:* `ops/main-guard-judges-the-command`
*Closed:* 2026-08-31 — authorised by the author, then fixed on that branch. `commits()` becomes
`commit_targets()` and reports **which repository** each commit is aimed at; `main()` judges each
one. Heredoc bodies are excised only for `cat` and `tee` with nothing carrying them onward. Six
tests fail against the previous hook and pass against this one, which is how the fix was checked
rather than asserted — and a fourth spelling, `GIT_DIR=`, was found by review of the fix itself and
would have left defect 1 alive in a different form.
*Now:* `.claude/hooks/main_guard.py` :: `    here = Path(cwd) if isinstance(cwd, str) else Path.cwd()`
*Status:* open

**`test_the_truth_is_not_lying_in_the_file_in_plain_sight` fails about 1 run in 254** · found
2026-08-31 · by `evals/world-cache-measured`, from one red in a suite run
**The failure a reader will meet:** `AssertionError: 248` at
`tests/corpus/test_world_seal.py:136`, `assert phrase not in raw, phrase`. It passes on retry. This
entry exists so that a search for that text lands here in one step, because at 1 in 254 it will fire
on somebody who knows none of this.

*Determinism is not implicated, and that was established before the cause.* The seal was generated
three times at the same seed and scale and compared field by field: `payload`, `nonce`,
`commitment_sha256`, `openings`, `world`, `seed` and `scale` are **byte-identical**. **One field
varies — `sealed_at`** — which is correct for a thing recording when it was sealed. Nothing the
seeded exact-arithmetic machinery produces is non-deterministic, so the cross-runner sha256 result
stands unqualified.

*The cause.* The test asserts five phrases from the truth do not appear in the sealed bytes. Four
are 62, 113, 23 and 6 characters. The fifth is `str(truth.totals["acks_failed"])` = **`'248'`**, and
it is tested against a string containing `2026-08-31T10:15:55.965333+00:00`. It fails whenever those
three digits land in the timestamp.

*The rate, measured over 200,000 simulated sealing moments:* `"248"` appears in the timestamp in
**785/200000 = 0.39%**, about **1 run in 254**. It is corpus-dependent — another world or scale
gives another `acks_failed`, and a two-digit value would fail far more often.

**And the finding above the bug is that the docstring is right.** It says the phrases are taken
*"from the truth itself… not from a list somebody wrote while thinking about what to hide. A
hand-written list would test the author's imagination; this tests the file."* That reasoning is
sound and it is the better design — **and it is why the defect exists.** Taking phrases from the
truth means taking whatever type they happen to be, and one of them is a small integer.

This is **not** *a guard tested by its author*. It is a guard that **removed** the author's judgment
and inherited the data's shape instead — usually right, and wrong when the data contains something
too small to be evidence. It is the first instance recorded here where **doing the correct thing
caused the defect**.

*Three fixes, none obviously best.*

**(a) Skip phrases below a length.** Reintroduces a threshold somebody chose, which is what the
docstring's design exists to avoid.

**(b) Search the `payload` rather than the whole file.** Also a narrowing, and in the direction
refused all day: the test currently covers every field, and narrowing means a leak into some other
field stops being caught. *Those fields cannot contain secrets* is an assertion that would need
demonstrating.

**(c) Exclude `sealed_at` by name, with a written reason.** It is the only field that varies —
established by measurement — and a timestamp is not secret. Removes exactly the source of the false
positives and keeps coverage of everything else. The same shape as `make language`'s excepted paths
and `unarmed_because`: **a named exemption carrying its justification, rather than a narrowed scope
carrying none.**

*And the ordering that solved it is the reusable part, not the fix.* The first question asked was
not *what makes it flaky* but **which side of the determinism line it falls on** — answerable in one
command, before anything about the cause was known, and if it had come out the other way it would
have been the most serious thing found that day rather than a footnote.

> **When an observation contradicts a measured property, establish whether it is inside that
> property's scope before investigating the cause.** The cause can take an hour; the scope question
> took one command.

*Site:* `tests/corpus/test_world_seal.py` :: `        str(truth.totals["acks_failed"]),`
*Disposition:* its own branch — a claim-adjacent test, and the choice among three fixes is a
judgment that should not ride on a branch about CI measurement
*Status:* open

**A limit was stated in review and did not reach the branch** · found 2026-08-31 · by oversight
level 2 on `evals/world-cache-measured`, by grepping for a word rather than reading for a claim
The measurement's own limit — *the sample lies inside one world-source epoch, so it says nothing
about a run where the worlds genuinely changed* — was written in review, correctly, an hour before
the branch was committed. **It appears nowhere in the branch.** The word `epoch` was absent from
every file; the artefact said *the difference is the cache alone* and *the cache saves about
eighteen minutes a job*, which is the wider claim the review had already identified as unsupported.

*It is the fourth restatement chain in one day to stop at the terminal, and the first where the
missing half was the **caveat** rather than the correction.* The other three lost a fix; this one
lost the sentence saying what the fix does not cover — which is the half nobody misses, because the
document reads as more confident without it.

*And the overstatement was not only a missing caveat.* Every cold run in the sample was a
**spurious** invalidation, so the measured 18.4 is **what a spurious invalidation costs**, not what
the cache **saves**. They share a number here only because no run in the sample ever needed to
regenerate. Where the world sources genuinely change, regeneration is necessary work no cache can
save. The branch's own over-coverage finding says that, and its summary sentence undid it three
files away.

*Corrected in all four places* — `ci.yml`, `docs/DECISIONS.md`, `PLAN.md`, `evals/README.md` — and
the correction **strengthens** the over-coverage entry rather than weakening it: the whole measured
effect is the price of the bug.

*How it was found is the reusable part.* Not by reading the branch for correctness, but by taking a
claim made in conversation and **grepping the artefact for it**. That is mechanical, it takes
seconds, and it is available for every limit either session states aloud. Nobody has to remember to
be careful; the check is *did the thing I said reach the file*.

*Site:* `PLAN.md` :: `review and **did not reach the branch until oversight level 2 grepped for it and found it absent**`
*Adopted, in two halves, because the first has the reviewer's memory in it.* What worked here was
one session happening to recall a striking sentence from an hour earlier — **which is not a
mechanism, it is the faculty that produced `42`.** Scaled to a week it catches whatever the reader
happens to remember. So the burden moves to the writer, at the moment they know it best:

> **A limit stated in conversation names the file it will land in.** *"That is a narrower claim
> than the cache saves 18 minutes — it goes in `ci.yml`'s comment."*

Then the check is `grep` against a **named file** rather than against recall. It costs four words
where the claim is made, and it is the same move as *carry the command*: the discipline lands on the
person asserting, while they assert, instead of on somebody later trying to remember. The reader's
grep still catches what it catches; this removes the need for it to.

*And the limit, stated rather than left to be discovered:* **neither half is a mechanism.** Both are
habits, and habits are what this repository exists to distrust — nothing goes red if either is
forgotten, and the failure is silent in the way every failure at this site has been.

*Disposition:* adopted as a working practice between the two sessions, in both halves, with the
limit above
*Closed:* 2026-08-31 — the instance corrected in four files, and the practice recorded rather than
left open with nobody able to close it
*Now:* `PLAN.md` :: `Every cold run in the sample was a **spurious** invalidation, so 18.4 is what a spurious`
*Now:* `evals/README.md` :: `**That last clause was a projection until 2026-08-31, and the number that replaced it is from a`
*Status:* open

**A branch name in the record is a checkable assertion, and nothing offline can check it** · found
2026-08-31 · by `evals/world-cache-measured`, which built the gate and measured it wrong
`docs/reviews/phase-1.md` named nine branches on 2026-08-30. One — **`evals/world-cache-measured`,
this one** — was never opened, and two sessions spent a day filing measurements into it: the
determinism result, three within-commit pairs, the budget argument. Nothing went red, because
nothing in the tree was wrong. The claim lived in a table and in conversation.

*It is the only form of the defect that has never lived in a file.* The other ten instances
`CLAUDE.md` catalogues were a sentence, a number in configuration, a deferral, a task note. This one
existed **only as shared narrative between two agents**, repeated until it stopped being checked.
`docs/reviews/phase-1.md` caught the one-author version of that in its own opening line — *"this
report existed only in a terminal until it was written here"* — and the two-agent version is one
step along.

*And two mechanisms were blind to the same absence.* `docs/DECISIONS.md` carried
*"the change `evals/world-cache-measured` makes"* as an unlock condition pointing at a branch that
did not exist, and `make expiry` could not see it because it checks a condition is **present** and
never that it is **reachable**. One instance is a mistake; two mechanisms blind to one missing thing
is a gap.

*The gate was built and then measured, and it is refused on its own numbers.* Branch names appear in
four positions that declare them as such — `TASKS.md`'s `branch`, `*Disposition:*`,
`*Unlock condition:*`, and a review table's `branch` column — which yields **49 names with no
judgment about which are branches**. That part works. Classifying each as merged, open or nowhere
does not: **12 of the 49 came out wrong**, including six merged branches reported as `nowhere` and
this branch reported as `merged` because its own name appears in a commit message.

*The reason is structural rather than a bug to fix.* A squash-merged branch **leaves no ref**, so
offline git cannot distinguish *merged and deleted* from *never existed* — the two states the gate
exists to tell apart. The authoritative source is `gh pr list`, and `make figures` runs inside
`make check`, which `CLAUDE.md` requires to work **local, with no account and no credentials**. A
gate that needs the network is a gate that is red on a plane.

*So it is filed rather than shipped, and the enumeration is the half worth keeping.* Reading four
declared positions gives the population for free and needs no judgment; only the git question is
unanswerable offline.

**Three options, priced, because the third was proposed after the first two and needed checking.**

**(a) A network check outside `make check`.** Authoritative — `gh pr list` answers exactly the
question. Cost: it cannot live in `make check`, which `CLAUDE.md` requires to run local with no
account. Red on a plane.

**(b) A weaker offline check** reporting *has a ref* / *has no ref*, saying plainly that it cannot
see a merged branch. Cost: it does not answer the question the gate exists for, since
*merged-and-deleted* and *never-existed* both report no ref — which is the pair that lost a branch.

**(c) Record the landing in the tree**, the way `docs/FINDINGS.md` records a closure, so a branch is
**open** (has a ref), **merged** (has a landing record) or **nowhere** (neither). Fully offline, and
its failure mode is the good one: forget to record a landing and the gate prints `nowhere` for a
branch that landed — one wrong line, no red run, and the wrongness prompts the recording. **A
recording step that decays announces its own decay.**

*Checked before believing it, and it does not work today.* `TASKS.md`'s closed registry already has
the shape — `branch <name> status closed`. Measured: of the 20 named branches the API says are
merged, **14 carry a landing record and 6 do not**, and **four records name a branch that never
existed**. Two of those four were written into this repository on 2026-08-31 — `docs/phase-1-review`
and `ops/coverage-expiry-findings` — because **the registry's shape assumed one branch per atom** and
an atom that spanned three got a name somebody invented to fill the column. They are corrected in
`TASKS.md` to name the three real branches each. Two older ones are not recoverable from the log and
are left, because inventing a second name to replace the first is the same act again.

So (c) is the best shape and needs the recording step repaired first, which is most of its cost.
Whoever takes this chooses with all three priced rather than discovering the third.

*Measured:* 49 names enumerated, 12 misclassified, by
`gh pr list --state all --json headRefName,state` compared against the offline classifier.

*Site:* `docs/DECISIONS.md` :: `*Unlock condition:* CI's world-cache budget being set from measurement — the change`
*Disposition:* `ops/the-record-names-a-place-that-exists` — after phase 1, with the CI work, since
both turn on what may run inside `make check`
*Status:* open

**The layout's fabrication check assumes the declared-future block sits last** · found
2026-08-31 · by oversight level 2 on `docs/the-documents-agree-with-the-code`
`layout_fabrications` isolates the present-tense half as `body[: future.start()]`. That is
everything **before** the declared-future heading, not everything **outside** the block. Move the
block into the middle of the section — a reorganisation, not an accident — and every entry below it
silently stops being checked for fabrication. The instrument examines less than it claims and
nothing reports the shrinkage, which is the coverage rule against the coverage module.

*Latent rather than live, and that is why it is filed rather than blocking.* It needs a deliberate
reorganisation of the section. `#31`'s `F1` needed only somebody copying an older window, which is
how contract windows actually get written — the difference between *somebody would have to decide
to do this* and *this is how the thing is normally done* is the whole reason one blocked a merge and
this does not.

*The fix is one line:* take everything outside the block rather than everything before it.

*Not moved by the cost of CI, in either direction.* At five-minute CI it would still be filed — a
fourth round on a green branch for a latent one-liner is disproportionate at any speed — and the
reviewing session applied that test before asking rather than after, which is the check against
finding a good reason for the decision you already wanted.

*Site:* `ops/figures.py` :: `present = body[: future.start()] if future else body`
*Disposition:* the branch that next touches `layout_fabrications`, or `#9` if nothing else does
first — one line, and it should not wait for a reason to exist
*Status:* open

**The closed registry calls itself complete and has no gate** · found 2026-08-31 · by
`docs/the-documents-agree-with-the-code`, while acting on the review's count of three
`TASKS.md`'s *Closed — the atoms that have landed* opens with *"kept so this file is the complete
registry, not just the open half"* and stopped at **L9**. `docs/reviews/phase-1.md` §3e found three
atoms missing on 2026-08-30. Acting on it on 2026-08-31 found **nine** — claim 2, claim 3, claim 7,
`SCENARIO.md`, the review itself, and four of the branches the review proposed. The section kept
asserting completeness while the work went on, so the gap grew between the finding and its fix.

*Why it is not simply a stale list.* It is a hand-maintained second copy of `git log main`: every
closed atom is a squash commit there. What it adds is what each atom **settled**, which the log does
not carry, and that is why it exists rather than being deleted. What it lacks is the thing every
other population in this repository now has — a second enumeration. It reports on what it examined
as though that were what exists, which is the coverage rule exactly, in a document rather than a
tool.

*Why it is filed rather than gated in the branch that found it.* Comparing entries to squash commits
needs a rule for what counts as an atom. Not every merged PR is one — `docs/phase-1-review` and the
ruleset fix were two commits closing one piece of work, and this branch closes three review findings
at once. A gate that counted commits would go red on correct history, which is the failure mode the
suite-count finding names. The rule is the work.

*Site:* `TASKS.md` :: `Kept so this file is the complete registry, not just the open half.`
*Disposition:* `ops/the-registry-is-enumerated-twice` — with the suite-count finding, since both are
*a present-tense claim in a document nothing re-runs* and a single rule may cover them
*Status:* open

**A published number never agreed with the eval that produced it, and level 2 passed it** · found
2026-08-30 · by oversight level 3 · *closed the same branch it was filed in*
`make claim-4` prints `green 12/12 checks` and `evals/censoring/README.md` lists C1…C12. **11/11**
survived in five places — `PLAN.md` twice, `TASKS.md` three times — because `C12` arrived in the
**same commit** that closed the claim, `86fe136`. So the number was never right, not once: there is
no moment at which the documents and the eval agreed and then drifted apart.

*What makes it worth an entry rather than a typo.* It passed oversight level 2 on the branch that
introduced it. A reviewer reading that diff would have seen a claim declared closed at 11/11 and an
eval printing 12/12 in the same change, and the two never sat on the same screen. It is the minuted
figure from `CLAUDE.md`'s catalogue of ten — an assertion checked against the artefact it came from
rather than against the thing that would falsify it, which here was one command.

*Measured before correcting, rather than taking the review's word:* `make claim-4` →
**12/12 checks, 9/9 mutations biting**. The review said 12/12 and was right, and it was still
checked, because a correction sourced from another document is the defect repeating itself.

*Corrected once and recorded once.* Five terse mentions do not each get a restatement block —
the delta lives here and in `PLAN.md`'s session entry, which is where doctrine rule 4's
requirement that the prior value and the reason stay recoverable is actually met.

*Site:* `PLAN.md` :: `make claim-4` is green at 11/11 checks with 9/9 mutations biting`
*Site:* `TASKS.md` :: `claim 4 green at 11/11 with 9/9`
*Disposition:* `docs/the-documents-agree-with-the-code`
*Closed:* 2026-08-31 — all five corrected, the number measured rather than copied from the review
*Now:* `PLAN.md` :: `somebody chose. `make claim-4` is green at 12/12 checks with 9/9 mutations biting, in about a`
*Now:* `TASKS.md` :: `L9  src/holdout/core/demand/, evals/censoring/, make claim-4 — claim 4 green at 12/12 with 9/9`
*Status:* open

**A guardrail rule id does two jobs, and a rename breaks the second one** · found 2026-08-31 · by
oversight level 2 on `contracts/floor-rule-id`, and the check that produced it was proposed rather
than assumed
**One rename cost a compatibility mapping and a guard; fifteen other rules can each do the same.**
A rule's `id` **names the rule inside a window** and **identifies the same rule across windows**.
Those are different properties carried by one string, so renaming for the first breaks the second —
and `RENAMED_RULES` in `envelope.py` is what you build when identity and spelling are the same
field. It is why the deferral did not anticipate the cost: it scoped a rename, and this was never a
rename.

*The check that settles whether a map is needed at all.* If resolving a decision meant finding the
applicable window and reading the id **in that window**, there would be nothing to map — the closed
window keeps its own spelling by contract rule 1, and each window is self-describing. So: what looks
a rule up by a single canonical name across all time?

**`envelope_as_of` does, and it does it sixteen times.** It resolves each contract rule into a
dataclass field by a hard-coded literal — `minimum_gross_margin_pct`, `cost_staleness_hours`,
`cap_benchmark`, `perishable_exemption` and twelve more. It cannot read "the window's own id"
because a window carries four or five ids and nothing says which one fills
`FloorRule.cost_staleness_hours`. The literal **is** the link, and it is the only one. So the map is
necessary in the current model, and **fifteen other rules carry the same latent cost**: each is one
rename away from needing its own entry.

*Three shapes, with their prices, so whoever takes this is choosing.*

**The map, which is what shipped.** Correct, guarded — a window carrying both spellings is refused,
because two rules with one meaning leave nothing able to say which was in force — and checked to
bite, since emptying it turns the suite red. Its price is that it accumulates forever and it puts
contract knowledge in the engine, when the contract layer is this repository's declared source of
truth. A real cost paid slowly rather than a defect.

**A window-scoped vocabulary.** Better placed, but it does not remove the map on its own: the
sixteen literals are the problem, and moving them into the contract only moves where the
correspondence is written.

**Separating identity from spelling** — a stable identity that never changes, and an `id` that is
the human-readable name within a window. Then a rename changes a spelling and nothing else, and no
map is ever needed. This is the real fix and it is a change to the **contract model**, so it may
not ride on a branch about one rule.

*And the rule is enforced in one direction only, which whoever costs the third shape should have in
front of them.* `accepted = (rule_id, *retired) if window.effective_from < renaming.since else
(rule_id,)` — so a window opened **before** `since` accepts the canonical name as well as the
retired ones. A 2025 window carrying `refuse_when_no_price_satisfies_every_guardrail`, a name that
did not exist in 2025, resolves silently. That is F1's mirror: F1 was an old name accepted in a new
window; this is a new name accepted in an old one, and the stated principle — *a window is read in
the vocabulary of its own time* — covers both.

**Deliberately not fixed on `contracts/floor-rule-id`.** The consequence is an anachronism in a
contract document rather than a wrong value; the fix would cost a fourth full matrix on a branch
that has had three; and the whole question disappears under the third shape, where a window's
spellings are its own and there is no cross-window name to admit. It is recorded here rather than
deferred separately because it is the same finding: one field doing two jobs, now visible from both
sides.

*What is not in question.* The refusal of a window carrying both spellings is right under all three
shapes and stays wherever the resolution ends up living.

*The map got a time bound before it shipped, and the review is what found it missing.* As first
written, `RENAMED_RULES` was keyed by guardrail and canonical id alone, with nothing scoping an old
spelling to *when* it was valid — so a window opened in 2027 carrying the retired id resolved
without complaint, undoing the rename the mechanism exists to serve. It reproduced before it was
fixed. `Renaming` now carries `since`, an old spelling is readable only in a window that opened
before it, and `tests/core/test_envelope.py` holds both halves — the refusal, and the historical
window still resolving, so the fix is a time bound rather than a ban. **The mechanism being a
symptom is unchanged by that, and is the finding.**

*Anchor re-aimed 2026-08-31, and the gate is what asked.* `make findings` reported `MOVED` when
`RENAMED_RULES` changed type from `tuple[str, ...]` to `Renaming` under this branch's own F1 fix.
The register says an anchor vanishing means the site was **rewritten** rather than restated, and
that only a person can say whether the finding was fixed. It was not: the map still exists, an id
still does two jobs, and the fix made the map *more* elaborate rather than less. So the anchor moves
to the line that carries it now.

*Site:* `src/holdout/core/guardrails/envelope.py` :: `RENAMED_RULES: dict[tuple[GuardrailId, str], Renaming] = {`
*Disposition:* its own branch, unlocked when **the contracts move in phase 2** — the event
`docs/DECISIONS.md` already declares for *"the generated SQL has never been executed"*: `phase 2,
when gold is built. If gold does not match, the contracts move`. That is the moment the contract
model is open anyway, and separating identity from spelling is cheap while it is being changed and
expensive at any other time. The two travel together
*Status:* open

**Two values reach the world cache as data rather than as an import, and one of them is silent**
· found 2026-09-01 · by T00G, and the second only because the reviewing session asked whether the
first was alone
`evals/uplift/cache.py` keys its entries on a digest of every **source file** a cached artefact was
produced by. That is the right rule for a ledger, which is a pure function of the world and of
`outcomes.py`. It is not the whole rule for one entry.

`agreement/walked` caches `reference.compute(run, metric=metric)`, and `reference.py` finishes with
`metric.rounding.canonical_integer(total)`. **The rounding arrives as an argument, out of
`contracts/metrics/`, not as an import** — so a change to the metric contract leaves that entry in
the cache while the value it stands for has moved. The key carries `world_id`, `world_seed` and
`scale.name`, and nothing about which metric was asked for.

*What it does today, measured against the code rather than feared.* The half it is compared with,
`grouped = outcomes.cell_margins(ledger, metric.rounding)`, is computed **fresh** on every run — the
*ledger* is cached, the margins are not. So after a rounding change `U10` compares a fresh value
against a stale one and **goes red**. That is the safe direction: a false failure, not a silent
pass, and it is why this is filed rather than fixed on sight.

*Why it is still a defect.* `cache.py`'s docstring says the exception *"is not a list of file paths
somebody keeps up to date"* and that changing any byte of what produced an artefact moves the key.
For this entry that is not true, and the gap is invisible to the very test written to close it:
`test_every_module_a_cached_artefact_is_produced_by_is_in_the_digest` walks the **import** closure,
and an argument is not an import. The test says so in its own docstring rather than leaving the
limit to be found.

*And the shape is the one this repository keeps meeting.* Not a claim checked against the wrong
artefact — **a rule whose scope is the mechanism its author had in mind.** *Every source file it was
produced by* is a complete rule for values produced by code alone, and this value is produced by code
**and a contract**. The digest is a second implementation of *what could change this*, and it is
implemented over one of the two.

*The fix is a widening and does not travel with a narrowing.* Two candidates, and the choice is not
obvious: put `metric.id` and `metric.version` **in the key**, which is local, precise, and rests on
`make contracts` refusing a metric whose arithmetic moved without a version; or add `contracts/` to
`DEPENDS_ON`, which is blunter, invalidates every world on any contract edit, and is the
over-coverage `cache.py` already argues against one directory in. **T00G is a narrowing**, and
shipping a widening in the same branch is how a cache change stops being reviewable — the two move
the key in opposite directions and a single measurement could not tell which one did what.

**And then the question that found the other one.** The reviewing session asked whether the
rounding was the only member of its class — *anything reaching the world-producing path as data
rather than as an import* — and said plainly it was asking rather than asserting, because inferring
what a generator reads from what generators usually read is the move that produced *matrix legs*.

**It was not alone, and the second one is worse.** `corpus/world/__init__.py`'s `prepare()` calls
`policy.contract_ladder()`, which reads `contracts/policies/ladder_policy@v1.yaml` at run time —
**the control arm of every fresh-markdown world**, and therefore the markdown behaviour the entire
ledger is a summary of. Driven rather than argued: moving one rung from `depth_pct: 20` to `25`
changed the policy and left the digest at `0b15f66b64bc0b4e69b6ab44decb144a`.

*The two fail in opposite directions, which is the whole reason they are one entry and not two.*
The rounding gap is compared against a half computed **fresh**, so a stale entry produces a red
`U10` — annoying, visible, safe. The ladder gap has nothing to disagree with it: every consumer
reads the same stale ledger, and the run reports a world built with the old ladder **in silence**.
That is a gate disarmed, which is the failure this repository has already paid for four times.

*So the ladder is closed inside T00G and the rounding is not, and the split is on the direction
rather than on convenience.* A proven silent hole is not something a branch may declare as a limit
while claiming its coverage is computed — that would be prose asserting a check nobody wrote, in
the branch whose subject is exactly that. The rounding stays open because it fails safe and because
its fix is a genuine widening with two candidate shapes.

*What closing it looks like, so it is not a second list.* `DEPENDS_ON` gains **one file**, not
`contracts/` — the rest of that directory reaches no world — and
`test_the_contract_the_generator_reads_is_taken_from_the_generator` takes the path from
`policy.LADDER_CONTRACT` rather than repeating it, so a generator pointed somewhere else cannot
leave the list behind. That is the second-registry problem one layer down, refused the same way.

*Site:* `evals/uplift/agreement.py` :: `        cache.key("agreement/walked", world_id, world_seed, scale.name),`
*Disposition:* the **ladder half is closed on T00G**; the rounding half is its own branch,
unlocked by T00G landing — after which the key has one meaning and a widening can be measured
against it rather than through it
*Status:* open

**The checks list cannot show a duplicate-context defect, and has hidden two** · found
2026-09-01 · by T00H, from a count that disagreed with an expectation that happened to exist
Sharding named eight jobs `claim-2`, so eight check runs shared one context name. `gh pr checks 41`
reported **nine** checks. The run had **sixteen** jobs.

*That is not a quirk of the tool.* `gh pr checks` answers *which contexts exist and did they
pass*. It cannot answer *how many runs produced them*, because same-named contexts collapse into
one row — so **any defect whose shape is a duplicate context name is invisible to it, by
construction**.

**Both of this repository's context-count defects have had exactly that shape.** `#39`'s doubling —
every context twice on every pull-request head — took pairing 200 runs on `headSha` to see. This
one took listing the run's jobs. **Twice, the convenient view was the one that could not show it.**

> **For anything about how many runs or jobs produced a result, the instrument is the jobs API or
> `/check-runs`. `gh pr checks` is for *did the named things pass*.**

*And the second half is why it was caught at all, which is the less comfortable one.* Nine looks
like a healthy checks list — five claims, `gate-proof`, `discover`, `gate`, `secrets` — and nothing
about it invites a second look. It was suspicious only because a matrix had just been **computed at
sixteen**, five minutes earlier, for an unrelated reason: the concurrency ceiling.

> **When a change alters how many things there should be, compute the expected count before
> running it, and compare.**

It costs a minute; it was the only thing that would have caught this; and it is available for
precisely the class of change that is otherwise hardest to verify — one that alters **structure**
rather than behaviour, where every individual thing still passes and only the arrangement is wrong.

*Neither half is a mechanism and both are habits*, which this repository distrusts on principle —
nothing goes red if either is forgotten. They are recorded because the failure they catch is
silent in the way every failure at this site has been, and because the first one is at least
checkable: a reader who sees `gh pr checks` used to count anything can say so.

*Site:* `.github/workflows/ci.yml` :: `    name: ${{ matrix.name }}`
*Disposition:* `evals/claim-2-sharded` (T00H) — the fix is in that branch with a guard and an
attack; this entry is the method, which no guard covers
*Status:* open

**`make language` enumerates repository content by a hand-written exclusion list** · found
2026-09-01 · by T00H, when the gate went red on a directory that branch created
`ops/language.py`'s `content_files` walks the tree and skips a `NOT_CONTENT` set of names —
`.git`, `.venv`, `.worlds`, `notes`, and now `.shards`. Every entry is generated or ignored
output, and every one had to be remembered.

*It went red the day sharding landed*, on eight pickle files under `.shards/` — enumerated as
repository content and not examined, which `make figures` correctly reports as under-coverage.
That is the list **working**; it is also the fourth time in four days that a hand-maintained list
has had to be extended by whoever tripped over it.

**The answer is already in the tree, one file away.** `ops/figures.py`'s `_layout_population`
was rewritten to ask git — `_tracked_paths()` runs `git ls-files`, and its docstring says *what
git tracks, which is the only defensible answer to what is repository content*. Its own comment
records that **nothing is excluded by name**, and the defect that produced it is the one where
`notes/` counted on the author's laptop and not on a clean checkout. `content_files` is the one
gate that did not get that move.

*So this is not "design a way to enumerate repository content".* It is applying a change that has
already landed, to the place it did not reach — which is why it is filed with `_layout_population`
named rather than left as a direction.

*Not taken on T00H*, deliberately: it is a change to a gate, inside a branch about CI wall clock,
and it costs a full matrix to land. Nothing about it is blocking.

**Second instance, 2026-09-02, and it carries the half that makes this worse rather than
longer.** `make language` went red on `.claude/worktrees/ops-ci-runs-once-per-tree/…/prior_price.yaml`
— a stray worktree left behind by `evals/claim-2-sharded` after it merged as `#41`. Untracked, and
the gate walks it anyway, which is the `notes/` lesson exactly: **a hand-written exclusion list
cannot know about a directory nobody meant to create.**

**And the direction is the one that matters.** That failure is **invisible to CI** — a worktree
exists on one machine and never on a runner — so the gate that would catch an untracked directory
**never runs where the directory is**. It is not that the list is one name short. It is that the
list is maintained on the only machine where the problem occurs and checked on the only machine
where it cannot. Two instances now, and the second one is not a longer list.

**Third instance, 2026-09-04, and it is the one that turns the list into a forecast.**
`make language` went red on **67 MB of Terraform provider binary** the day `T013` created the
first infrastructure layer — `infra/lakehouse/.terraform/providers/…/terraform-provider-databricks_v1.130.0`,
enumerated as repository content and undecodable, which `make figures` correctly reported as
under-coverage. `.terraform` is now the third name added to `NOT_CONTENT` by whoever tripped over
it, and **`git check-ignore` answers in one line**: `.gitignore:60: infra/**/.terraform/`.

> **Every one of the three is a gitignored artefact the gate had no business reading, and each was
> added by the session that met it.** `.shards/` when sharding landed, a stray worktree that
> reddened one laptop and no runner, `.terraform/` when the first Terraform layer landed.

**So the pattern is no longer *the list is short*. It is a prediction: the next tool adds a
fourth.** Nothing about these three is a judgement call — `git ls-files` would have excluded all
three without an entry, and `ops/figures.py` has asked git since 2026-09-01, one file away, with a
docstring saying *what git tracks, which is the only defensible answer to what is repository
content*. The entry stays open because the change has still not been made, and each instance is
cheaper to add than to fix, which is exactly why three of them exist.

*Site:* `ops/language.py` :: `NOT_CONTENT: frozenset[str] = frozenset(`
*Disposition:* its own branch — small, and unblocked now rather than by anything. **Three
instances, and the third is the argument for doing it before a fourth**: the fix is applying a
move that already landed one file away, not designing anything
*Status:* open

**The combine job's worlds are disjoint from every shard's** · found 2026-09-01 · by T00H, from
measuring a cold combine rather than reasoning about one — so sharding splits the world cache
along with the phases
`make claim-2`'s draws now run on eight machines and are judged on one. The judging step is not a
merge: `report()` calls `_truths()`, which generates **counterfactual** worlds — a control-arm and
a treatment-arm generation per world seed for W6, W4 and W5 — and the agreement checks, which
generate and then walk five million events.

*Measured on this repository's corpus:*

```
warm combine                       1s
cold combine                     596s     _truths 411s · U11 195s · U10 51s
whole unsharded harness, warm    270s
```

**A cold combine costs more than twice the entire run it was meant to speed up.** Both cold and
warm combines are byte-identical to the unsharded baseline, so nothing is wrong with the
arithmetic; it is entirely the world cache.

*And the diagnosis is sharper than the one two sessions had reached independently.* We both said
*the cache is partial* and both proposed per-shard keys. Per-shard keys do not fix this: **no
shard's cache can contain what the combine needs**, because a shard builds a fixture and draws
against it while the counterfactual generations are different entries entirely. It is not that the
cache is partial. **The combine's work is disjoint from every shard's.**

*Today's unsharded run hides it* by doing draws and truths in one process, so `.worlds` ends up
holding both and the next run restores everything. Splitting the phases splits the cache with them.

*What T00H does, and what it does not.* Two key families with one writer each — per-shard for the
draw phase, one for the combine, **the same digest in both** — so the tail is **cached rather than
removed**, paid once per world-source change. `tests/ops/test_ci_sharding.py` drives six attacks
against those keys.

*What would remove it, with the reason it is safe, so nobody has to rediscover it.* Move the
counterfactual generations into the shards. That looks unsafe because `_truths` takes its units
from the **globally-first** record with outcomes, and a shard holds an interleaved subset — a
different first record, different units, a different truth, and the byte-identical comparison
gone. **But the expensive half takes no units at all:** `counterfactual_unit_weeks` returns the
full control and treatment maps and `average_treatment_effect` filters them afterwards. So a shard
can generate the maps and the combine can still choose the units over the whole set.

*Site:* `.github/workflows/ci.yml` :: `          key: worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}-combine`
*Disposition:* its own branch, unlocked by **T00H landing** — after which the key families exist
and a change that moves work between phases can be measured against them rather than through them
*Status:* open

**`ci.yml` is entered twice for every branch push** · found 2026-09-01 · by this session, while
scoping the other three CI items — and the pair was already in this register under another name
`on: push:` carried no branch filter while `pull_request` was scoped to `main`. A push to a branch
with an open pull request fired **both**, so the whole workflow ran twice for one sha — not two
matrix legs, two workflow runs, seconds apart.

*The measurement, from the run list paired on `headSha`:*

```
gh run list --workflow=ci --limit 200 --json databaseId,event,headSha,conclusion,createdAt
```

200 runs, 2026-08-27 to 08-31 — 118 distinct head shas, **81 of them under both events**. Job
timing from `/actions/runs/{id}/jobs`:

```
across the 81 doubled shas:  push 586 jobs 3542 min · pull_request 586 jobs 3478 min
one whole side redundant:    ~58 h of runner time in five days
of which claim-2 alone:      2092 min = 34.9 h
successful claim-2 jobs:     n=90, 78.4 h; 35 shas succeeded under both events
                             → 27.9 h duplicated = 36% of all successful claim-2 compute
```

**Roughly 8x the cache over-coverage**, which is 11 spurious invalidations at +18.4 min = 3.4 h over
the same period, and which was the item ranked first when the work was scoped.

*The second effect, stated at the strength the data carries and no higher.* Every context existed
twice on every pull-request head sha — `gh api /repos/.../commits/<sha>/check-runs` returns 20, every
name doubled, including all three the `main` ruleset requires. So each required context was resolved
between two check runs of one name from two runs of one tree.

**The hazard was never realised.** All 36 merged pull requests carried doubled contexts at their head
sha, and in **zero** did a required context disagree with itself. Three self-disagreements exist —
`gate` twice, `claim-1` once — and **all three sit on commits superseded before the pull request
merged**, so the ambiguity decided nothing. Whether the forge takes the latest check run or either
one is **not established here and is not guessed at**: after the filter a head carries one run of
each context and the question cannot arise. **The fix dissolves it rather than answering it**, which
is the better outcome and should be read as one — nobody later needs to know how it would have
resolved.

*The first draft of this entry did not say that.* It said *a gate whose verdict depends on which run
the forge happens to read*, and the reviewing session restated it back in stronger terms still. It
was withdrawn against the 36 merge heads before the branch was written. **Agreement from the
reviewer is exactly the moment a finding stops being examined**, and that is the only reason this
paragraph is here.

*And the pair was already in this register, measured, under a description that hid it.* The entry
below reads *"each being one commit's two matrix legs, same tree, same push, same cache key"* and
names runs `33358845044, 33358846344` at 1.01x apart. Those two are the **push** run and the
**pull_request** run of `7b1fd6c`. The figures are right and the conclusion drawn from them — that
the distribution to size a budget against is the distribution over runners — survives untouched and
is if anything strengthened, since two runs on two runners is exactly what they are. What was wrong
is the phrase *two matrix legs*: it named the observation correctly and made the reason for there
being two invisible. **Nobody asks why a pair is a pair when the word for it already implies an
answer.**

*And the first draft of the fix had the defect it was written about, found within the hour by
its own successor.* It wrote `pull_request: branches: [main]` — the spelling every example uses.
With `push` scoped to `main`, a pull request opened against **any other base** then matched
neither event and got **no CI at all**: `#40`, stacked on `#39`, reported *no checks reported on
the branch*, and the unscoped `push` had been covering that case by accident until an hour
earlier.

**The exposure paragraph was right about what it examined and wrong about what exists.** It
measured *a push with no pull request* — 3 of 118 shas — and never asked about *a pull request
whose base is not `main`*. Stacking one reviewed piece of work on another is this repository's own
practice, so the uncovered case was not exotic; it was the next branch. `pull_request` therefore
carries **no** branch filter, which costs nothing and doubles nothing, because `push` fires only
on `main`.

*It is the eighth form of a guard tested by its author, and the sharpest available here:* the
branch whose subject is *a gate reports on what it examined* shipped an exposure claim measured
over the shape its author pictured. `tests/ops/test_ci_triggers.py` now parametrises the base over
`main` **and** a working branch, so the case is driven rather than assumed.

**And the general form is one turn tighter than that, which is worth separating because it is not
the same rule.** *A gate reports on what it examined* is about a **check's population**. This is
about a **change's obligations**:

> **It enumerated what the change stops firing, and not what the change still has to fire.**

*A push with no pull request* — 3 of 118 — is a count of what the filter **removes**. *A pull
request whose base is not `main`* is a case the filter had to keep **covering**, and did not. Two
different questions, and only the first was asked. **When a trigger is narrowed, the enumeration
that matters is what must still run.**

*The mechanism that caught it earns its own line, because nothing else would have.* `#40` existed
to be **stacked on `#39`**, so the uncovered case was produced by this repository's own working
practice within the hour. A change that shipped alone would have hidden it until the next time two
pieces of work stacked — and no reading found it, including a review that had approved the
paragraph.

*And the fix retires an instrument, which is named here rather than discovered later.* The
duplication was two independent runs of one tree on two runners, free, on every push. It is what
established that this machinery is deterministic across machines, and it is where every same-tree
spread figure in the record came from. **After the filter the pairs stop being produced.** The
evidence stays valid and becomes historical; reproducing it deliberately is `workflow_dispatch` on
the same sha, twice.

**And the register under-counted its own instrument by seven-fold.** This entry reasoned from two
pairs and the reviewing session recalled five. Re-pulled from the same 200-run sample, `claim-2`
succeeded under both events on **35 shas** — 35 same-tree, two-runner comparisons, ratio min 1.00,
median 1.10, max 1.69. The conclusion they were used for is unchanged and better supported. What is
new is that a measurement nobody had to ask for was arriving on every push and being noticed one
time in seven, which is the same shape as the pair itself: **the thing that goes unexamined is not
the thing that is hidden, it is the thing that arrives without being requested.**

*Site:* `.github/workflows/ci.yml` :: `  push:`
*Disposition:* `ops/ci-runs-once-per-tree`, `TASKS.md` :: `T00F` — first of the four atoms that open
phase 2, and before `T00H` for a structural reason as well as a cost one: concurrency peaks at 16
jobs against a ceiling of 20 *because jobs double*, and six shards do not fit until the doubling is
gone
*Status:* open

**`claim-2` costs an hour and the whole matrix re-runs on every push** · found 2026-08-31 · by the
author, and decided rather than deferred
`claim-2` runs on one machine at **32m17s to 1h18m18s** against a 90-minute timeout, and every
intermediate push re-runs the full matrix. On `#30` that meant three draws for a pull request that
needed one — the branch, the review fixes, then a follow-up — with one cancelled at 65 minutes and
two superseded. The question raised was whether an hour a run is what a professional would do. The
answer taken: **the cost per run is justified and the dead time is not.**

*And the within-commit spread is a draw, not a constant — which is what the second pair
established.* Two pairs are now measured, each being one commit's two matrix legs, same tree, same
push, same cache key:

> **Restated 2026-09-01: they are not matrix legs.** Runs `33358845044` and `33358846344` are the
> **push** run and the **pull_request** run of `7b1fd6c` — the whole workflow entered twice for one
> sha, because `on: push:` carried no branch filter. The numbers stand and the conclusion stands;
> what does not is the word that made the pair look like a property of the matrix. **A description
> that already implies an answer is where nobody asks the question** — the finding above is what it
> hid, and it is ~8x this entry's own cache item. The prior wording stays per doctrine rule 4.

| commit | legs | apart |
|---|---|---|
| `7b1fd6c` (#30) | 32m30s · 32m47s — runs 33358845044, 33358846344 | **1.01x** |
| `46b8225` (#27) | 32m17s · 54m39s | **1.69x** |

One pair agreed to within seventeen seconds; the other disagreed by twenty-two minutes. So there is
no *within-commit variance* to use as a headroom multiplier — **one pair predicts nothing about the
next**, and the distribution to size a budget against is the distribution over **runners**, not over
commits and not over pairs. The pair that agreed is as much a measurement as the pair that did not,
and it is the one that would have been dropped as unremarkable. The honest summary of the sample:
eight or more measured runs, **32m17s to 1h18m18s, 2.43x**, with the maximum having moved once. It
is *the largest number seen so far is not the largest number*, one level along.

*Two fixes, neither of which changes what is proved.* **Sharding `claim-2` across its six worlds**
is the large safe win — the same work on more machines, nothing skipped, roughly six-fold on wall
clock, with a combine step as the real cost because the eval prints aggregates across worlds. **A
merge queue** is second: the expensive matrix once, on the merged result, rather than on every
push. `#30`'s two superseded runs are the measurement that justifies it.

*And path filtering is refused, by name and in advance.* Skipping `claim-2` when only documents
change reintroduces **a claim that silently does not run**, which is precisely what `discover` and
`claims-complete` were built to make impossible — the `claim-[1-7]` defect bought back for a saving
in minutes. It will be proposed as the obvious cheap fix, and this line is here so that whoever
proposes it meets the refusal before the argument.

*The practice that costs nothing and was adopted immediately:* finish a piece locally, run
`make check` and the relevant `make claim-N`, and **push once**. Where a review produces findings,
apply all of them and push the result. That captures most of a merge queue's benefit with no
engineering.

*The revisit trigger was written, restated and then retired inside a day, and the retirement is
the measurement.* It read first *"more than two pushes"*, then *"more than two full-matrix runs
through incomplete work"* — the second because a rebase forced by somebody else's merge is a push
and is not waste, and counting it would penalise the discipline rather than the waste.

**`contracts/floor-rule-id` then ran the full matrix three times and every one was legitimate.**
The first push complete and green; the second forced by `bec0e7f` landing on `main`; the third by a
review finding that had to be fixed. **Not one was work pushed before it was finished** — which is
precisely what the trigger counted — and roughly three hours of compute happened anyway.

*So the trigger is withdrawn rather than restated a third time.* A condition that cannot fire on
three hours of real waste is not a safety valve; it is a number that makes its author feel measured.
What replaces it is not another trigger but the evidence it failed to capture: **one branch, three
justified matrices, and a merge queue would have made it one.** That is a stronger argument for the
second fix than the trigger ever was, and it came from the trigger failing rather than firing.

The prior wordings stay per doctrine rule 4, and the delta is the finding: **a trigger is an
assertion about what the system does, wearing a number instead of a verb** — and this one was
written against the failure its author imagined rather than against the runs that actually
happened.

*Site:* `.github/workflows/ci.yml` :: `timeout-minutes: 90`
*Disposition:* its own branch, before the first Terraform layer — phase 2 is where the push rate
multiplies, and CI is what everything else depends on, so rebuilding it mid-phase risks the defect
it protects against. Phase 1's six remaining branches are four documents and two small ones; they
do not justify rebuilding the thing that judges them
*Status:* open

**The corpus describes an industry median as the benchmark a Greek instrument defines** · found
2026-08-27 · by oversight level 2
The third of three blocking findings against claim 1, and the one that left the record. Two
statements are wrong and they are separable.

*The equivalence.* `corpus/real/` states that Eurostat's gross margin over **turnover** is *the same
quantity* ΥΑ 21330/2026 άρθρο 4 παρ. 4 calls ΠΜΚ, a margin over the **selling price**. The same
denominator *family* is defensible; the same quantity is not. Turnover is not the selling price of
one product code, and an industry median is not a trader's own average. The article does not
contain the equivalence; it was read in. `corpus/real/README.md` then attributes the exactness of
`m / (1 − m)` to that alignment, which makes a fact of algebra depend on a legal claim that is not
in the text.

*The benchmark.* The instrument anchors the benchmark to the trader's own 2025. The corpus uses a
2008–2020 industry median and `evals/guardrail/build.py` calls it *"The published 2025 gross
margin"*, which is wrong on both words that matter, at the point closest to the arithmetic — and it
**is** the cap's benchmark: `sector_wide_benchmark_on_price()` feeds `ProposedPrice.benchmark_markup_on_cost`
on all 232,373 decisions claim 1 drives.

*What does not move.* **Claim 1 does not reopen**, and the reason was written three weeks before
anybody needed it: the eval prints on every run that it does not prove the numbers in
`contracts/guardrails/` are the right ones, only that the machinery honours whatever envelope it is
handed. `contracts/guardrails/regulated_basket.yaml` keeps its benchmark symbolic and sourced, so
the contract does not implement the law with a median either. What does not survive unqualified is
the **scenario** claim — a corpus presented as real, citing a live Greek regulation, whose concrete
benchmark is a construct that regulation does not use.

*The article behind it was also miscited*, which is its own entry below — split out on
2026-08-31 because the two have different files, different fixes and different landing dates, and
one entry covering both meant one anchor answering for two defects.

*Corroboration, labelled as what it is:* the reviewing session opened a secondary source
reproducing the decision's full text on 2026-08-31 and reports both articles verbatim. Not the
gazette, not opened here, and nothing above depends on it.

*How the scenario half was settled, which was not ours to settle.* The prose sites are defects and
were fixed. What was left is a judgment about the product: a corpus presented as real, whose
concrete benchmark is a construct the regulation does not use, is either an acceptable declared
limit or a claim the corpus should stop making. The author decided: **real inputs, derived cost** —
the wording becomes precise everywhere the corpus is described, and *real* does not stand alone with
the derivation in a footnote. Six sites carry it now: this directory's README and `__init__`, the
manifest header, the attack's own docstring in `evals/guardrail/checks.py`, the eval's README, and
`docs/SCENARIO.md`. The prices, endings, dispersion, markdowns, regulated list and margin statistic
are real; the unit cost is a construct, and it is named as one every time.

*Site:* `corpus/real/README.md` :: `That alignment is not a`
*Site:* `corpus/real/MANIFEST.yaml` :: `Eurostat's ratio is gross margin on goods for resale over turnover,`
*Site:* `evals/guardrail/build.py` :: `The published 2025 gross margin`
*Disposition:* branch `corpus/legal-claims-restated`
*Closed:* 2026-08-31 — `corpus/legal-claims-restated` landed. The four sites are restated with their prior wording kept beside them per doctrine rule 4; the corpus's benchmark is named `sector_wide_benchmark()` at every call site rather than reshaped, because the per-code shape was already in the core; and the author decided the scenario half — *real inputs, derived cost*, stated wherever the corpus is described rather than *real* alone with the derivation in a footnote. Claim 1's output is bit-identical to `b7ab2ae` over 232,373 decisions, sha256 `22a6daea…`.
*Now:* `corpus/real/README.md` :: `So the accurate description of what claim 1 is driven by is`
*Now:* `corpus/real/MANIFEST.yaml` :: `It is a corpus device for deriving a plausible`
*Now:* `evals/guardrail/build.py` :: `A sector median over 2008-2020, standing in for a quantity no public dataset contains.`
*Status:* open

**The finding miscites the article it rests on** · found 2026-08-31 · by the reviewing session
Split out of the entry above on 2026-08-31. `PLAN.md`'s record of oversight level 2's third
blocking finding said ΥΑ 21330/2026 **άρθρο 4 παρ. 5** *"defines the benchmark as the trader's own
average, per product code, over 2025"*. παρ. 5 defines **Περίοδος Αναφοράς** — the reference period,
per undertaking, keyed to that undertaking's own last closed financial year. The per-product-code
average is defined elsewhere in the instrument.

*The conclusion survives and the citation does not.* The benchmark is still anchored to the trader's
own 2025, so a 2008–2020 sector median is still not it. What would have been imported into the fix
is the wrong article, by a restatement that repeated the wording it was correcting.

*Provable inside the tree, with no external source, which is the part worth keeping.*
`docs/REGULATORY.md` and `corpus/real/MANIFEST.yaml` both have παρ. 5 right; `PLAN.md` had it wrong.
**Two documents agreed, a third disagreed, and nothing compared them** — for four days, in one
repository. That is the argument for this file rather than a footnote to it.

*Site:* `PLAN.md` :: `defines the benchmark as the trader's own average, per product code, over 2025`
*Disposition:* branch `corpus/legal-claims-restated`
*Closed:* 2026-08-31 — restated in `PLAN.md` by `corpus/legal-claims-restated`, with the prior wording kept beside it per doctrine rule 4
*Now:* `PLAN.md` :: `benchmark to the trader's **own** 2025 rather than to a sector figure.`
*Status:* open

**Half of `G7` cannot fail, and half of `C7` cannot either** · found 2026-08-31 · by oversight level 3, while arming it
`G7.closed-vocabulary-only` asks two questions and one of them is a dead branch. *Is every reason's
code one the vocabulary declares* is checked as `reason.code.value not in declared` — and
`reason.code` **is** a `RefusalCode`, so the condition can never be true. The type already closed
the vocabulary; the check re-asks a question the type had answered.

*What is not wrong.* `G7`'s second question is real and load-bearing: **every refusal carries a
detail**. Claim 1's evidence is *which* guardrail refused, and a code with no detail says a price
was refused without saying what about it was wrong. That half is now armed —
`17-a-refusal-arrives-without-its-detail` blanks the detail, moves no bound, certifies no price and
changes no code, and `G7` is the only check in the eval that falls.

*So the check is not removed and the figure is not touched.* `12 distinct codes over 365,591
reasons` is a real published number; what is dead is one `if`. Deleting it would lose the statement
that the vocabulary is closed, which is true and worth asserting somewhere — the question is whether
a check is the right somewhere when a type already guarantees it, and that is a judgment about where
a guarantee should live rather than a defect to patch.

*Why it is here rather than fixed in the branch that found it.* The branch's subject is arming
unarmed checks. Rewriting one of them while arming it would mean the mutation was written against a
check nobody had reviewed in its new shape — and `evals/README.md`'s rule 5 is that a boundary is
computed twice, not that a check is edited by whoever is proving it bites.

*And the same fact a second time, in `C7`.* Found by oversight level 2 reading this branch, and
recorded here rather than as its own entry because it is not a second finding: it is the same
question with a different type answering it. `C7.the-graded-days-are-not-the-days-the-curve-was-
fitted-on` asks whether the held-out segment is disjoint from the fitting segment, and `overlap`
is drawn from two complementary predicates over one business date — so that half cannot be
non-empty either. Its other half, *is neither segment empty*, is real and is a property of the
corpus. Two entries for one fact would be the mirror of what this register caught in its first
hour, when one entry was answering for two defects and had to be split.

*What this branch did change.* `C7` carried the tautology as its stated reason for being
un-armable. That reason is now the half that can actually go red, because the sufficient reason
was always the corpus one — leaving an assertion of a dead branch sitting in prose, in the branch
whose whole subject is that such assertions get filed rather than mentioned. The `if` itself is
untouched in both checks, for the reason above.

*Site:* `evals/guardrail/checks.py` :: `if reason.code.value not in declared:`
*Site:* `evals/censoring/checks.py` :: `overlap = [origin for m in worlds for origin in m.keys_in_both_segments]`
*Disposition:* none — a judgment about whether a check should re-assert what a type guarantees
*Status:* open

**The suite count is published where no gate can read it** · found 2026-08-31 · by oversight
level 2, after writing a wrong one
Every session entry in `PLAN.md` ends with `The suite is **N**`, and nothing recomputes it. `PROSE`
in `ops/figures.py` is the mechanism that would, and it excludes `PLAN.md` deliberately: the file
keeps superseded figures forever per doctrine rule 4 — 965, 965, 959, 943, 937, 928 are all in it
and all correct as written — so re-running a number there would go red on history.

*The argument is sound for the history and silent about the newest entry.* Only the last one is
present tense. It is the only figure in the file that is a claim about now, it is the one a reader
takes as current, and it is outside every gate in the repository.

*Found by writing one.* `The suite is **976**` went into `PLAN.md` as a projection — one test added,
one replaced, arithmetic — in the same change whose subject is that an assertion wearing a number is
set from a measurement of the thing that runs. It is **972**. Nothing caught it; an agent
reconsidering caught it, about ninety seconds later. That is not a mechanism and it does not survive
a tired session, which is the whole argument of `docs/reviews/phase-1.md` §2 and the reason this is
filed rather than shrugged at.

*What the fix is not.* Registering `PLAN.md` in `PROSE` as it stands would go red on six historical
figures immediately. What is needed is a rule for *which* occurrence is present tense — the last, or
one carrying a marker — and that is a judgment about the document, which is why it is a finding and
not a patch.

*A candidate, offered with its two checks already run, to be tested by whoever takes the branch
rather than adopted from here.* The four-kinds rule marks a published number `[M]` measured, `[D]`
declared, `[C]` cited, `[S]` scenario. If figures carried their kind, *present tense* would stop
being a judgment about position and become a property the text carries — a superseded figure is no
longer a measurement of anything, it is the record of one — and `PROSE` could register `PLAN.md`
and re-run exactly the marked ones. It is the same move as selecting on `where` rather than on a
name prefix, one file along.

**Check one fails as stated, and that is the important half.** `PLAN.md` contains eight marker
occurrences and every one of them is prose *about* the four-kinds rule, in the session entry that
introduced it. **No figure in the file carries a kind, and no suite line carries one.** The
repository has the vocabulary and applies it in `docs/SCENARIO.md`, where `**320 stores [M]**` and
`**[M]** python -m ops.roster --scale <name>` sit beside their commands. So the distinction is not
already here waiting to be read; it exists elsewhere and has never been applied to this file.

**Check two passes, and more cheaply than it was feared to.** Precisely *because* no figure here is
marked, adopting this rewrites none of the six historical lines — they are already unmarked, which
is the state the rule wants history to be in. Nothing doctrine rule 4 protects gets edited, and the
change is forward-only.

**What neither check found, and what the branch will actually have to answer.** The marker has to
*migrate*. If `figures` re-runs every marked figure, then the session after next must take the
marker off this entry's `972` or that number goes red the moment the suite grows — so every session
boundary carries a small edit to the previous session's line. Removing a marker does not change a
stated value, so it is not a rule 4 violation, but it is routine editing of superseded text, and it
is the kind of step that gets forgotten. A forgotten marker is a red on correct history, which is
the failure that teaches people to delete markers rather than to write them. **Any version of this
needs the migration to be enforced by the same gate, or it decays into exactly the noise it was
built to remove.**

*A second candidate, and it is the one that removes the migration rather than paying it.* The
marker has to migrate only because the present-tense figure lives in a file that cannot be
overwritten — every session must demote the last one precisely because `PLAN.md` keeps it forever.
Give the current count a home that **can** be overwritten and there is nothing to migrate: `figures`
covers that one place and re-runs it every time, and this file's numbers become history by
construction rather than by anybody remembering to demote them. `PLAN.md` then stays outside `PROSE`
legitimately rather than by judgment — not *we cannot tell which occurrence is present tense*, but
**nothing here is present tense, because present-tense figures are not written here.** One
enforceable sentence: an append-only file records what a number was; a current number lives where it
can be replaced.

**What it costs.** A home has to be chosen and created, which is a judgment about where a reader
would look — and the measurement says there is no candidate today: the count exists in `PLAN.md`
ten times and `TASKS.md` once, both append-only, and **nowhere in the tree is there an
always-current home for it.** No README line, no gated file.

**And the phrasing half is not free, which is the check that decides between the two candidates.**
The reading that *The suite is 828* inside a dated entry already reads as history does not survive
being measured. Of the ten occurrences, **exactly one sits directly under a dated header.** The
other nine sit under an intra-entry bold sub-heading — `**The denominator is in the type.**`, `**And
`C7` carried the same defect as `G7`, in the same commit.**` — which carries no date; the session's
date is twenty to sixty lines above. The suite figure is always the last line of an entry and
always the furthest from the only thing that marks it as past. Skimmed or quoted, it reads as
present tense, which is precisely how it is read.

*(The entry headers also use three different date separators, so any gate that tries to find the
newest entry by parsing them meets the wrap-and-pattern family from the other direction.)*

**So the nine would need rewording, which is the objection this candidate was raised to avoid.** It
is not a doctrine rule 4 violation — *the suite was 828 at this session* changes no stated value and
leaves the value, the reason and the delta recoverable — but it is editing text rule 4 protects, and
that is the thing to say out loud rather than discover in the branch.

**Which leaves the two candidates separated by one property, and it is not the one either of them
was argued on.** The marker's cost is **recurring**: one edit at every session boundary, forever,
and forgetting it turns correct history red. The new home's cost is **one-off**: nine lines reworded
once, plus a home that has to be chosen. A recurring cost that decays into deleted markers is worse
than a one-off cost that is simply work, so the second candidate is the stronger of the two — but
both are recorded with their prices, because whoever opens that branch should be choosing rather
than implementing.

*Site:* `ops/figures.py` :: `#: **Deliberately small, and the reason is doctrine rule 4.** `PLAN.md` and `TASKS.md` are the`
*Disposition:* `ops/the-newest-figure-is-present-tense` — small, and it belongs where the count is
published rather than in the branch that found it
*Status:* open

**A mutation may name a check that does not exist, and the cheap target cannot tell** · found
2026-08-31 · by oversight level 2, on `evals/unarmed-checks`
A mutation declares `targets:` — the checks it expects to refuse it. Nothing in `make gate-proof`
asks whether those names correspond to a check that exists. `engine.py` does ask, at
`unknown = [target for target in mutation.targets if target not in baseline]`, but only with the
eval loaded, which means only inside `make claim-N`. The ledger's own docstring gives as its reason
for existing that a mutation which has come unmoored is caught by the cheap target as well as by
the expensive one, and this is the one way of coming unmoored it does not catch.

*It is the sibling of `every-anchor-is-aimed-at-one-place`*, which asks exactly this question one
level down — does a mutation's anchor still occur in the source it names — and the implementation
is the same shape. What made it newly cheap is this branch: `declared_checks()` enumerates every
check id in the tree in milliseconds, so the comparison is now a set difference.

*This branch does not create the hole; it adds a quieter place for it to land.* Before, a renamed
check left its mutation failing at run time in `engine.py`. After, the same rename lands that check
in **unarmed** — printed, counted, and deliberately not refused. The mutation still fails when
`claim-N` runs, so nothing is unproven; what changes is that the cheap target now has a state that
looks like an honest backlog and can be reached by a typo.

*Measured today, so that tomorrow's non-zero is legible:* 37 distinct mutation targets, 67 declared
check ids, **0 naming nothing**. By
`python -c "from evals.gate_proof.ledger import load_mutations, declared_checks;
print(sorted({t for m in load_mutations() for t in m.targets} - {d.id for d in declared_checks()}))"`.

*Site:* `evals/gate_proof/ledger.py` :: `armed = sorted(i for i in by_id if i in targeted)`
*Disposition:* `evals/mutations-point-at-checks-that-exist` — a different assertion from this
branch's, so a different closed piece of work
*Status:* open

**`pricing/selection.py` serves no claim, and the review that said so assigned it nowhere** · found
2026-08-30 · by oversight level 3
`src/holdout/core/pricing/selection.py` is reached by no eval and targeted by no mutation. Only
`tests/core/test_pricing.py` and `tests/core/test_composition.py` touch it. It is on `CLAUDE.md`'s
declared decision path — *the model returns a scenario table, code picks the row by arithmetic* — so
deleting it is not the answer; **naming** it is. Either claim 1 brings it into its sweep, or it is
written down that scenario selection is proved by the suite and not by a claim.

*How it was lost, which is why it is here.* `docs/reviews/phase-1.md` closes with a nine-row table
assigning every section to a branch. §4 is not in it. The only reference to the module anywhere
outside its own source and tests is the review's own line — not in `TASKS.md`, not in `PLAN.md`, not
in `docs/DECISIONS.md`, no branch, no task, no deferral. It was found by its author, in his own
document, the day after writing it.

*Why it is the register's second entry rather than a branch tonight.* Naming a branch for it now
would repeat the error the assignment table already made once: assignment written quickly, at the
end of a long document, with no mechanism behind it. It is held here until somebody scopes it with
the module in front of them.

*And it is the entry that tests the half nothing else does.* The legal finding had two sides that
drifted apart, which a cross-check catches by construction. **This one never had a second side at
all** — recorded once, never picked up. A cross-check would find nothing to compare and report
nothing. It is caught only by *anchored against adrift*, which was specified for completeness rather
than for a case anybody had in hand, and then a case arrived.

*Site:* `docs/reviews/phase-1.md` :: `One module: **`src/holdout/core/pricing/selection.py`**`
*Disposition:* none — to be scoped by whoever picks it up, with the module in front of them
*Status:* open

**`CLAUDE.md` and `TASKS.md` disagree about whether phase 4 gets an integration review** · found
2026-08-31 · by `skills/integration-review`, while writing the skill that runs one

`CLAUDE.md`'s oversight table says level 3 runs *at every phase boundary, without exception*, and
the emphasis is deliberate — the argument beside it is that a review which is remembered rather
than scheduled is the one that stops happening. `TASKS.md` carries **T016** for phase 2 and
**T024** for phase 3 and nothing after phase 4: `T026` closes the phase and closes the project,
and the registry ends there.

**Neither document is wrong on its own, which is why nothing found it.** `PLAN.md` phrases each
one as *before the next phase opens*, three times, and after phase 4 there is no next phase — so
the absence agrees with `PLAN.md` and disagrees with `CLAUDE.md`, and a reader of any one file
sees nothing. It is the shape T00D and T00E already have in this repository and that
`docs/reviews/phase-1.md` §3c has one layer up: two files each correct alone, with nothing
computing the product.

**What is at stake is not tidiness.** Phase 4 is where claim 6 lands — the one `CLAUDE.md` calls
*the one nobody builds* — and where the agent surface arrives. If level 3 does not run after it,
the last conceptual-drift read of this repository happens **before** its most novel claim exists,
and the phase that closes the project is the one phase no integration session has read. The
opposite reading is equally defensible and belongs in the same breath: an integration session
exists to protect the phase that comes next, and after phase 4 nothing does — on which reading
`T028`'s publication work is what inherits the job, and it is not a drift read.

**Which document moves is a judgment and not an inference**, which is why this is filed rather
than fixed. Either `CLAUDE.md` says the review runs before every phase boundary rather than at
every one, or `TASKS.md` gains a phase-4 task that `T028` waits on. The first is an edit to
`CLAUDE.md`, which is the author's; the second changes what closes the project.

*And it was found by writing the procedure rather than by running it*, which is the one thing here
worth generalising and is deliberately not generalised: one instance. Level 3's own subject arrived
while its skill was being extracted, from reading two documents against each other because the
skill had to state which task ids invoke it.

*Site:* `CLAUDE.md` :: `It is scheduled, not remembered: at the end of every phase, without exception.`
*Site:* `TASKS.md` :: `id            T026          <- closes Phase 4, closes the project`
*Disposition:* none — the reconciliation is an edit to `CLAUDE.md` or to `TASKS.md`'s phase-4 block,
and which of the two moves is the author's call rather than a session's, so it is filed adrift
instead of being given a branch it would be the wrong session to open
*Status:* open

**A guard covered naming exhaustively and the artifact's path not at all** · found 2026-09-02 ·
by the session sent to fix the run it produced

`tests/ops/test_ci_sharding.py` guards the transport between claim 2's eight shard jobs and the
one job that judges them. `check_the_draws_travel` asserts the artifact's **name** against the
download's **pattern**, that a shard producing nothing fails where it knows, and that
`merge-multiple` is set. Four properties, every one of them about naming.

It never asserted anything about the **path**. `actions/upload-artifact` has filtered every
path whose name begins with a dot since v4.4, before the glob is judged, and the directory is
`.shards/`. So run `33483742285` ran `make claim-2 N/8` to success on all eight machines,
uploaded nothing on any of them, and failed at the last step of each — eleven to sixteen
minutes of runner time per shard, discarded. The combine, which needs the shards, never ran.

**This is not *a guard tested by its author*, and the difference is the finding.** That defect is
an author testing their own assumption, in the shape their assumption already handles. Here the
author was not testing an assumption at all: the session that wrote this check had, in the
change immediately before it, fixed a defect where eight shards reported under one context
**name**. Naming was the topic in front of them. The guard they wrote covers naming exhaustively
and covers the path not at all — not because the path was assumed safe, but because it was not
the subject. **A guard covers the topic its author had in mind, and the topic is set by whatever
they were just doing.**

It is why the fix is stated generally — *any* path component beginning with a dot requires
`include-hidden-files` — rather than as a rule about `.shards`. A check written to the instance
would be the same defect a third time, scoped to the case that produced it, which is the reason
`CLAUDE.md` gives for not writing a rule at three instances.

*Site:* `tests/ops/test_ci_sharding.py` :: `def check_the_draws_travel(path: Path) -> None:`
*Site:* `.github/workflows/ci.yml` :: `include-hidden-files: true`
*Disposition:* branch `evals/claim-2-sharded` — the check and its attack land with the one-line
fix, and the entry closes when that branch merges with the sharded run green, which is also the
first evidence that the upload works at all
*Status:* open

---

**One anchoring rule, two populations, and only one of them had it** · found 2026-09-02 · by
the same session, one command later

This file requires every `*Site:*` fragment to occur in its file **exactly once**. The section
above says why in as many words: *zero means the line moved or was fixed; two means the anchor
is ambiguous and proves nothing about which line was meant.* It has been enforced since the
registry existed.

`tests/ops/test_ci_sharding.py`'s attacks anchor the same way — each names a fragment of
`ci.yml` and replaces it — and the rule had never been carried across. `_broken` asserted the
fragment was `in` the file and replaced the **first** occurrence.

**What that costs was demonstrated rather than argued, by accident.** The change above added a
comment over the upload step explaining why `if-no-files-found` is set to `error`, quoting the
setting. The attack that flips it then edited the comment, left the step exactly as it was, and
every check passed — so `test_each_attack_is_refused_by_some_check` reported *no guard exists
for this attack* against a guard that was working perfectly.

**It failed loudly only by luck of direction.** An attack that starts editing prose reports a
missing guard, which is noisy and false. The same mis-anchoring one step further along — an
anchor whose second occurrence is another *step* rather than a comment — reports that the guard
bit, on a file where the step under attack was never touched. That is `gate-proof` switched
off, printing green. Any of the seven attacks could have been in that state and nothing would
have said so.

**The generalisation is the entry, not the fix.** The fix is `== 1`. The finding is that a rule
argued once, in the file that invented it, does not travel to the next thing that anchors — and
this repository now has two populations that anchor a fragment to a file and one more (`Now:`)
in the same document. The next one will need the same sentence, and nothing enumerates the
populations that anchor.

*(And the rule cannot anchor to itself. A `*Site:*` naming `docs/FINDINGS.md` quotes the
fragment on the site line, which is then a second occurrence in the same file, so the gate calls
it ambiguous — driven, not deduced: this entry tried it and went red. The rule is therefore
cited by section here rather than anchored, and the limit is small but it is real.)*

*Site:* `tests/ops/test_ci_sharding.py` :: `f"the attack {attack!r} anchors on text occurring {found} time(s) in ci.yml. Zero means "`
*Disposition:* branch `evals/claim-2-sharded` — the `== 1` half is fixed in the change that
produced it; what stays open is that nothing enumerates which populations anchor a fragment to a
file, so the third one will arrive the same way
*Status:* open

---

**`make expiry` judges in UTC against dates written in the author's local day** · found
2026-09-02 · by the same session, from an age column reading `-1d`

`ops/expiry.py` and `ops/findings.py` both compute today as `datetime.now(UTC).date()`. The
dates in `docs/DECISIONS.md` and in this file are written by the author, in Athens, on the
author's calendar. For part of every local day the two disagree, and `is_expired` compares
`expires <= as_of` against the UTC one.

**Measured across every hour of 2026 rather than reasoned from the offset**, DST included:

    hours where the local date and the UTC date differ:  940 of 8,760  (10.7%)
    largest lag between the local day starting and UTC agreeing:  3:00:00
    ever a whole day:  no
    ever early:  no — Athens is never behind UTC, so the gate cannot fire before its date

**So this is hours, not a day, and that is the whole of why it is filed low rather than fixed.**
A deferral that expires on the 2nd goes red at 03:00 local rather than at 00:00; a finding filed
at 01:00 prints its age as `-1d`. CI runs in UTC throughout, so the two never disagree with each
other — only with the calendar the dates were written on.

It is recorded because the direction was not obvious before it was measured. A gate that fires
**late** is a different object from one that fires **early**, and only one of the two would have
been worth stopping for; nothing in either module says which it is.

*Site:* `ops/expiry.py` :: `as_of = args.as_of or datetime.now(tz=UTC).date()`
*Site:* `ops/findings.py` :: `today = as_of or datetime.now(UTC).date()`
*Disposition:* none — the fix is a timezone the repository would have to declare, which is a
decision about whose calendar the dates are in rather than an edit, and at three hours it does
not earn a branch of its own. It is here so the next person who sees `-1d` finds the measurement
instead of taking it for a bug in the arithmetic
*Status:* open

> **Restated 2026-09-04 by `pipelines/silver-reference-carries-the-product-dimension`, which is
> the `-1d` this entry predicted, arriving.** A finding filed at 01:30 local — 22:30 UTC — printed
> its age as `-1d`, exactly as the paragraph above says it would, and `make findings` stayed
> **green**: the age is reported, never asserted on, so this prints oddly and gates nothing.
>
> **What is new is not the symptom. It is what the symptom nearly did to the record.** The first
> response to `-1d` was to date the entry `2026-09-03` — the day the *instrument* is in — which
> would have made the row read `0d` and left a finding filed on the 4th recorded as the 3rd.
> **That is adjusting the record until the measurement agrees with it**, by the session that had
> just measured the instrument to be the thing that was wrong. It was caught by a reviewer, not
> by the author, and not by anything mechanical: nothing here can tell a date written a day early
> from a date written correctly.
>
> So the entry gains one line rather than a fix: **when the age column and the calendar disagree,
> the calendar is the record and the column is the symptom.** The prior wording stays per doctrine
> rule 4, and it needed no correction — it already named `ops/findings.py` beside `ops/expiry.py`
> and already named `-1d` as the shape. **It was right, and it was read after the mistake rather
> than before it**, which is the only reason this restatement is about a near-miss instead of a
> defect on `main`.

**A crash and a survival get the same words in `gate-proof`'s red line** · found 2026-09-02 ·
by run `33571168520`, the first `combine` job this repository has ever run

    FAIL  the-grouped-path-rounds-like-a-price-not-like-the-contract    CRASHED
          the eval did not finish within 900s
    mutations planted 8 · bit 7/8 · CRASHED 1
    RED  1/8 checks failed: the-grouped-path-rounds-like-a-price-not-like-the-contract

**Nothing about a gate is known there, and the last line names a mutation as though a gate had
gone quiet.** The mutated eval was killed at its budget, so it never produced a verdict and no
gate was ever asked. `SURVIVED` is the verdict that says a gate did not bite; `CRASHED`,
`STALE` and `NOT-ARMED` are facts about the harness. `evals/report.py` calls all of them
`checks failed`, because at that layer a mutation is a check like any other and the wording is
right for every other eval.

**And the detail line could not be read either.** *did not finish within 900s* is the same
sentence whether the run needed 902 seconds or four thousand, and those are opposite findings:
the first says a budget has no headroom on this hardware, the second says the mutation turned
the eval into a loop, which is what the budget exists to catch. Nobody reading that run could
tell which had happened, and the arithmetic available from the outside — `gate_proof` at 1391s
here against 1421 · 1432 · 1421 · 1455 · 1351s on `main` — bounds it without deciding it.

**Measured once the seconds existed: 747s, 83% of the budget, while the other seven sat between
32s and 86s.** And the two runs are *not* a spread — the tree changed between them, because
`COPIED` carries `.worlds` and `claim-2-tests` had moved out of the combine — so there is one
observation and no variance estimate. **The second arrived on the very next run — 826s, 92% —
which is the point: the sentence claiming one observation was written one run before there were
two, and the seconds are what made the second free.** 747 and 826 under the same arrangement are
1.11x apart and both under 900, with the later one 74 seconds from the limit. The variance of
the job they live in is measured and wider:
paired on `headSha` over the 200 runs before `#39` removed the doubling, 33 trees ran `claim-2`
twice, widest same-tree pair **1.69x**, median **1.09x**, and 1931s to 4698s end to end. The
comment beside `TIMEOUT_SECONDS` carries it, and nothing there proposes a number.

So the engine now prints each mutation's wall clock beside its verdict and publishes
`slowest mutation — Ns of a 900s budget (N%)` on every run, **including green ones**: the
headroom is the figure a later session needs in order to size `TIMEOUT_SECONDS` from a
measurement, and it can only be read while nothing has failed yet. `TIMEOUT_SECONDS` was raised
from 300 to 900 once already, on a laptop, and this is `CLAUDE.md`'s *assertion wearing a number
instead of a verb* arriving inside `gate-proof` itself.

**What is not fixed is the red line**, and deliberately: it belongs to `evals/report.py` and is
correct for the five other evals. What this layer can do is name the difference, so the note now
says in as many words that a `CRASHED` mutation tells you nothing about the gate it points at.

*Site:* `evals/gate_proof/engine.py` :: `f"killed at the {TIMEOUT_SECONDS}s budget. That is the budget and not a "`
*Site:* `evals/report.py` :: `f"  RED    {len(failed)}/{len(report.checks)} checks failed: {', '.join(failed)}",`
*Disposition:* branch `evals/claim-2-sharded` — the timing and the note land with it. What stays
open is the shared red line, which is one wording for six evals and a decision about the report
shape rather than about this one
*Status:* open

---

**A cache that can only warm on success, on a job that is failing because it is cold** · found
2026-09-02 · by reading the combine job's cache steps

`actions/cache` restores at the start of a job and saves in a post step **that runs only when
the job succeeds**. Run `33571168520`'s combine job shows both halves:

    Cache not found for input keys: worlds-Linux-d5d27bdca303d9be70f3b07057bee8a7-combine
    Post Run actions/cache@…  skipped

The key had never been written, because no `combine` job had ever passed — that run was the
first one to exist at all. And it wrote nothing, because it failed. **Every future combine job
starts cold for the same reason, and the run is partly slow because it is cold.**

**It is not circular for the mutation that actually failed**, and that distinction is the point
of filing it rather than blaming it. Mutation 07 edits `evals/uplift/outcomes.py`, which is in
`cache.py`'s `DEPENDS_ON`, so it moves the digest and regenerates every world it needs whatever
the cache holds — `engine.py` says so beside `TIMEOUT_SECONDS` and it was equally true on
`main`. A warm cache would not have saved it.

So the loop is real and it is not the cause here. It is filed because *it will be warm next
time* reads true and is false, and because the same shape sits under every one of these keys:
**a first-of-its-kind job cannot inherit a measurement from a job that has never succeeded.**
The same is true of the eight shard keys, which were all cold on that run — so the 490–973s
shard durations and the 1.99 max/min are the **cold** case, and the warm case has never been
measured in this repository.

*Site:* `.github/workflows/ci.yml` :: `key: worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}-combine`
*Disposition:* none — nothing here is broken and there is nothing to fix until a warm run
exists. It is a note against the next reading of those durations, so that a cold number is not
inherited as though it described the steady state
*Status:* open

**Claim 2's rounding mutation is expected to cross its budget, and that red is not a gate**
· found 2026-09-02 · by three runs of the combine job, filed before the red rather than after it

**If you are reading this because `make claim-2-combine` went red on that mutation with
`CRASHED`, stop here: nothing is wrong with the gate it names.** The mutated eval was killed at
`TIMEOUT_SECONDS`. No gate was asked, `U10.truth-implementations-agree` has not gone quiet, and
the fix is not to widen an assertion.

Measured, printed by `gate-proof` on every run since the seconds were added:

    33571168520   killed at 900s   — a different arrangement; `.worlds` carried ~11 MB more
    33577549272   747s   83% of the budget
    33581480860   826s   92% of the budget
    33584456101   528s   59% of the budget

**This entry was filed after the first three lines and said *1.11x apart, trending up*. The
fourth line arrived on the next run and there is no trend — there is a range.** 528 · 747 · 826,
**1.56x across three**, none of them over 900. The prior wording stays per doctrine rule 4 and
the delta is the finding, for the second time in the same paragraph: reading a direction off two
points is the same defect as reading a spread off two incomparable ones, which is what produced
this entry in the first place. **Three is not a distribution either.**

What survives all three is the shape rather than the direction. The seven other mutations in
that claim sit between 32s and 86s, so this is not a slow suite — it is one mutation, and
`engine.py` says why beside `TIMEOUT_SECONDS`: it edits `evals/uplift/outcomes.py`, which is in
`cache.py`'s `DEPENDS_ON`, so its run legitimately regenerates every world it needs. That is the
design working. **Whatever crosses first will be this one**, and the entry's first sentence is
what it is for.

The variance of the job it lives in is measured too — paired on `headSha` over the 200 runs
before `#39` removed the doubling, 33 trees ran `claim-2` twice, widest same-tree pair **1.69x**,
median **1.09x**. At the median, 826s is 900s exactly; at 1.56x from the highest observation it
is 1289s.

**Filed before it happens, which this repository has not managed before.** Every previous
instance of *a correct red that surprises its reader* was written after somebody had already
been surprised — and one of them, this same mutation at the old 300s budget, is why the budget
is 900. The whole content of the entry is that the search a person will run when they meet the
red should land here.

**Not fixed here, and the two candidate fixes are named so nobody has to re-derive them.**
Raising `TIMEOUT_SECONDS` a third time is the reflex the deferral beside `ci.yml`'s
`timeout-minutes` argues against, and it would be set from two observations. The other is to
stop the mutation paying for a regeneration that is not what it tests, which is **T00L's**
territory (this read `T00K's` until 2026-09-02; T00K is sharding and cannot fix it) — the same 826s sits on the critical path of the whole run, so the two arrive
together and neither is opened here.

> **The prediction landed, 2026-09-02, and it is a measurement now.** This entry called itself
> *"a prediction with a search term attached, not work"*. The search term hit on run
> **33610996234**, `claim-2 combine`: `the-grouped-path-rounds-like-a-price-not-like-the-contract`
> **CRASHED, killed at the 900s budget, 100% of it**, taking `claims-complete` — a required
> context — red with it.
>
> **Four observations now, and the fourth is not a duration because the job was killed before it
> produced one:**
>
> | when | run | result |
> |---|---|---|
> | (recorded here previously) | — | 747s · **83%** |
> | (recorded here previously) | — | 826s · **92%** |
> | 2026-09-02 06:45, `main` @ `83171e9` | 33600284036 | 806s · **90%** · passed |
> | 2026-09-02 08:48, `docs/day-one` @ `c9902bf` | 33610996234 | **900s · 100% · KILLED** |
>
> **The tree that crossed is the tree that did not, plus five Markdown files.** `docs/day-one`'s
> whole diff is 621 inserted lines across `PLAN.md`, `TASKS.md`, `docs/DAY-ONE.md`,
> `docs/DECISIONS.md` and this file — no Python, no contract, nothing on any path this mutation
> regenerates. So the variable is the runner and not the repository, which is what three
> observations spanning 747–826 already implied and what nobody could state until one of them
> went over.
>
> **This is `CLAUDE.md`'s fourth form of the rule arriving on its own terms** — *a timeout, a K, a
> tolerance, a threshold, a budget is an assertion about what the system does, wearing a number
> instead of a verb.* `TIMEOUT_SECONDS = 900` asserts *this mutation finishes in 900 seconds*, it
> was set from observations that all sat under it, and it is now false on the hardware that runs
> it.
>
> **Nothing is changed here and the reason is the entry's own.** Raising the budget a fourth time
> is the reflex the deferral beside `ci.yml`'s `timeout-minutes` exists to refuse, and it would
> again be set from below. The two named exits are unchanged: **set `TIMEOUT_SECONDS` from a
> measurement** — for which this table is now the measurement, and it says the budget must clear
> a ceiling nobody has yet observed rather than the 900 it was pinned under — **or T00K removes
> the regeneration this mutation pays for and is not testing.** Both are decisions, and neither
> is this branch's.
>
> **What it blocks, said plainly:** `docs/day-one` cannot merge, because a required context is
> red for a reason that has nothing to do with its diff.

*Site:* `evals/gate_proof/engine.py` :: `#:     747s (83%)  ·  826s (92%)      two observations, 1.11x apart, both under 900`
*Site:* `evals/gate_proof/mutations/claim-2/07-the-grouped-path-rounds-like-a-price-not-like-the-contract.yaml` :: `eval_module: evals.uplift.machinery`
*Disposition:* none — it is a prediction with a search term attached, not work. It closes when
`TIMEOUT_SECONDS` is set from a measurement or when T00K removes the regeneration, and either
of those is a decision rather than an edit
*Status:* open

**A commit onto `main` is permitted when the guard cannot lex the command** · found 2026-09-02 ·
by T015, by being refused four times — and **the permitting direction was found by `projects-0a`
reading the mechanism rather than the observations**
The guard judges a repository the command did not name whenever it falls back, and which way that
errs depends on which side the session is sitting on.
`main_guard` falls back to a regex when a command will not lex, and the fallback answers
`[None]` — *judge the session's own directory*. **It does not carry over the `-C <path>` that is
sitting in plain sight in the command it just failed to parse**, so the branch judged is the branch
of a repository the command did not name.

**Measured, by feeding the hook crafted `PreToolUse` events** — the two shared checkouts on this
machine, one on `main` and one on `docs/day-one`, each command naming the *other* with `-C`, and
lexability computed by calling the hook's own `_segments` rather than assumed:

| | what the command does | lexes? | judged against | hook |
|---|---|---|---|---|
| **A** | commit **onto `main`**, from a branch | **no** | the cwd | **ALLOWED** |
| B | commit **onto `main`**, from a branch | yes | the `-C` path | REFUSED |
| C | commit onto a branch, from `main` | **no** | the cwd | REFUSED |
| D | commit onto a branch, from `main` | yes | the `-C` path | ALLOWED |

**B and D are the tokenising path working exactly as designed. A and C are one defect facing two
ways, and A is the one that matters:** the guard's single job is to refuse a commit onto `main` at
the only moment refusing it is free, and in row A it does not.

**The file already wrote this sentence about a different door.** Its own account of the `-C` defect
it fixed reads: *"the branch was read from the session's directory instead — which refused a safe
commit into a worktree and, **worse, allowed** `git -C <the checkout on main> commit` from a session
on a branch."* That is rows C and A verbatim. **The fix closed both in the parsed path and neither
in the fallback**, which was not re-read when the parsed path was corrected — the file's own stated
pattern, *a flag this file already handles for one purpose is a flag it can be asked about for
another, and the second question is asked by a different function, written later, by somebody
reading the first list and not the file*, with `-C` recovery in place of a flag.

**The trigger is an ordinary English commit message.** The file knows the mechanism and says so — *"a
heredoc with an apostrophe in it is exactly what unbalances the lexer and sends us here"* — and the
message that produced the four real refusals contains six apostrophes, which is unremarkable for
English prose about somebody's connector and somebody else's design. What the file does not say is
where the fallback then looks.

**The docstring's cost model is what fails, and only in its last word.** It reasons that on an
unparsable command *"guessing wrong in the safe direction costs a retry and guessing wrong in the
other costs the branch"*. The asymmetry is right and the fallback is not on the safe side of it:
**`[None]` is only conservative for a session sitting in the repository it is committing to.** For a
session in a worktree — this repository's mandated practice whenever a peer session is live in the
shared checkout — it names a different repository than the command does, and once it does, *which*
way it errs is decided by which side the session happens to be sitting on rather than by anything
about the command.

**What is not claimed: `main` is not unprotected.** The ruleset refuses the push and has no bypass
actors, which the file's own opening states is the gate and is not in question. The loss is exactly
the thing this hook exists for and nothing more — the commits that then have to be unpicked, and
*"the temptation, at minute nineteen, to just push"*.

**And the first attempt at the table above asserted a column it had not measured.** It used
`-m "don't"`, called it unlexable, and got REFUSED / ALLOWED for rows A and C — the opposite of the
truth — because an apostrophe inside double quotes lexes perfectly and the fallback was never
reached. A probe built to test an assumption carried one of its own, in the column that was the
whole point of it. It is recorded because it is the same defect as the entry it was measuring, one
layer out, and because the corrected probe computes lexability instead of labelling it.

**Three doors, and the third one is priced rather than argued.** Proposed by `projects-0a`; the
figures are this branch's.

1. **Teach the fallback to find `-C`.** Refused: a second enumeration kept in step by memory, in the
   file that has had exactly that defect three times.
2. **Leave it.** Row A stands.
3. **Refuse when the command does not lex.** *Not* find the target in a command we could not parse —
   that is door 1 wearing a disguise — but **a commit whose target cannot be determined is
   refused.** No enumeration at all, and fail-closed is the direction this repository takes
   everywhere else. Row A becomes REFUSED, which is the whole point; row C is already REFUSED and
   does not move.

**Door 3's cost is friction and it is measurable, so it was measured** rather than described.
Every commit on `main` was rebuilt into the two command shapes a session actually writes and put
through the hook's own `without_written_heredocs` + `_segments` — the hook lexes the *command* and
never the message, so the message alone answers nothing:

| the shape a session writes | would not lex |
|---|---|
| `git commit -q -F - <<MSGEOF` … `MSGEOF` | **34 of 43 · 79.1%** |
| `git commit -m "<subject>"` | **0 of 43 · 0.0%** |

**79.1% is a frequency of inconvenience, not a refusal rate, and the difference decides the
choice.** It is not *79% of commits refused*, and it is not even *79% would need `-F`* read as a
burden. It is **how often the heredoc shape would have to become a two-step** — write the message
to a file, then commit with `-F`. Measured, both halves are clean:

| | lexes? |
|---|---|
| `cat > msg.txt <<EOF` … `EOF`, apostrophes and all | **yes** — a *written* heredoc, excised by `without_written_heredocs`, so nothing is triggered |
| `git commit -q -F msg.txt` | **yes** |
| `git commit -q -F - <<EOF` … `EOF` | no — this is the only shape that breaks |

**So the choice is between a guard that lets through the one thing it exists to stop, through a
door the file itself calls *worse*, and one extra command when a commit message is long.** Anyone
weighing 79.1% as four commits in five being blocked has been misled by the figure, which is why it
is stated this way rather than as a percentage on its own.

**And the fact underneath all of it, written on its own line because it has now been wrong three
times in three different hands:** *an apostrophe inside double quotes lexes perfectly.* It is why
`-m "<subject>"` is a clean **0 of 43**; it is why the first probe labelled `-m "don't"` unlexable
and returned the opposite of the truth for the two rows that were its entire point; and it is why
the naive reading of this defect comes out backwards **in exactly one place and keeps being that
place.** The next person to reason about apostrophes here will be wrong the same way unless they
run it.

**And the 79% is a property of this repository rather than of git.** These messages are unusually
prose-heavy by house style — apostrophes, em dashes and quoted sentences in every body — so the
figure is close to a ceiling for the shape, not a floor. What it does establish is that door 3
would be felt on nearly every commit here, which is a real cost and is the author's to weigh
against a guard that currently lets the one thing it exists to stop through a door the file itself
called *worse*.

*Site:* `.claude/hooks/main_guard.py` :: `    return [None] if _COARSE.search(command) else None`
*Site:* `.claude/hooks/main_guard.py` :: `#: prose inside a heredoc, and a heredoc with an apostrophe in it is exactly what unbalances`
*Disposition:* **the author's** — a hook enforces a rule he reserved to himself, and the harness
applies it whether a session consents or not. Filed rather than fixed for a second reason as well:
the obvious repair — teach the regex to find `-C` too — is a second enumeration kept in step by
memory, which is the defect this file has already had three times. The workaround for the refusing
direction costs nothing and is written down here: pass the message as a file,
`git -C <worktree> commit -F <path>`, with no heredoc on the line
*Status:* open

**`U10` compares two implementations and is armed from one side of the comparison** · found
2026-09-02 · by T015, while measuring what became T00L
**It is not an unarmed check, and saying so first is the point.** The arming unit in this
repository is the *check*, and `make gate-proof` classifies all 67 of them — **37 armed · 23
declared un-armable · 7 unarmed**. `U10.truth-implementations-agree` is in the armed 37: mutation
`07-the-grouped-path-rounds-like-a-price-not-like-the-contract` bites it on every run. So this does
**not** belong in the *21 of 57* family that `#30` closed, and filing it there would have been a
finding invented out of the wrong unit.

**What is true is narrower and is about which side.** `U10` exists to compare two implementations
of one metric definition — `evals/uplift/outcomes.py`, the grouped path, and
`evals/uplift/reference.py`, the deliberately slow one that *"may not share a line with it"*.
Measured over all eight of claim 2's mutations: **one is planted on the grouped path and none on
the reference path.** So what is demonstrated is that `U10` catches a defect introduced on the side
the production code will become; nothing has been shown about a defect on the side the comparison
is anchored to.

**Why that asymmetry is worth a line rather than a shrug.** The reference implementation is not a
test helper — it is the independence claim 2's `U10` rests on, and `CLAUDE.md` says the pair
*"doubles as a fourth, independent check of claim 5"*. A defect planted there and **not** caught
would say something quite different from the same defect on the grouped path: it would mean the
comparison can be anchored to a wrong number. Nobody has asked.

**And there is a cost reason it may have gone unwritten, which is not an excuse but is a fact.**
`reference.py` is one of the five entries in `evals/uplift/cache.py`'s `DEPENDS_ON`, so a mutation
planted on it invalidates the world cache exactly as mutation 07 does — measured on run
33600284036, that is **806s against its seven siblings' 32–87s, roughly 90% of it world
regeneration**. A mutation nobody wrote because it would cost twelve minutes is a mutation whose
absence was decided by a budget rather than by an argument. **T00L removes that cost — but only for the consumers.** A mutation planted on
`by_unit_week` or `window_mean` becomes cheap; one planted on **`compute`**, this path's
producer, still invalidates the cache and still pays the rebuild, correctly. So T00L does
not unblock this entry: it unblocks the cheaper half of it, which is exactly the half that
tests less.

*Site:* `evals/uplift/reference.py` :: `is the other implementation, and **it may not share a line with it**. It`
*Site:* `evals/uplift/agreement.py` :: `        id="U10.truth-implementations-agree",`
**Two options, and they are not the same kind of thing — which `23 declared un-armable` will
otherwise disguise.**

- **Plant a mutation on `reference.py`.** Cheap once T00K lands, and until then it costs the 806s
  above.
- **Declare it un-armable, with a stated reason.** This is a real option and 23 checks already
  carry it — **but not for this kind of reason.** Those 23 *cannot* be armed: a property of the
  corpus, a predicate with no bound, a check that would be a tautology. **This one can be armed
  and has not been**, and the difference between *impossible* and *unaffordable* is the whole
  content of this entry. Nor is the subject a helper: `reference.py` is the anchor of the
  independence claim 2 rests on, so declaring it un-armable is declaring that **the anchor of an
  independence argument cannot be tested** — a considerably larger sentence than any of the 23
  carries, and one that should be written out in full by whoever signs it rather than inherited
  from a count.

*Disposition:* its own branch, unlocked by **T00L landing** — after which planting on a
consumer costs what planting on any other file costs, while `compute` does not. Not folded into
T00L: that task is about where a function lives, and this is about which side of a comparison has
been attacked
*Status:* open

**A task's identity was taken from a sentence about it, and the sentence named the wrong task** ·
found 2026-09-02 · by T00L, and by `projects-0a` naming its own half first
The `TIMEOUT_SECONDS` entry says the second way out of the rounding mutation's budget is *"to
stop the mutation paying for a regeneration that is not what it tests, which is **T00K's**
territory"*. **It is not.** `T00K` is *Shard claim 2's mutations* — parallelising nine serial
runs — and sharding cannot fix that flake at all, because `TIMEOUT_SECONDS` is applied
**per mutation, to its own subprocess**: `07` would still take ~800s and still be killed at 900s
on whichever shard drew it.

**Two sessions then spent two hours designing "T00K" without either of them opening `TASKS.md`.**
The reviewing session named its own half of it first and in the sharper form: *twice now I have
taken a task's identity from a sentence about it rather than from the task* — the same shape as
telling the author for three days that phase 2 was Terraform. **A wrong cross-reference that
nobody follows costs nothing; this one was followed, and cost two hours of design against the
wrong closing condition.**

It was caught the way the other one was: by opening the file the sentence pointed at, immediately
before building, rather than by any amount of reasoning about the sentence.

**And `T00K`'s own `closes` carries a second one, measured rather than argued.** It says *"Nine
near-equal units, so the balance interleaving had to buy for the draws is free here"*. Measured on
run 33600284036 they span **32-87s against 806s — 25x**, so the balance argument rests on a
near-equality that does not hold. After T00L the spread is **32-87s, about 2.7x**, which is better
and is **still not near-equal**; the entry is restated with both spreads rather than with a claim
that T00L makes the sentence true.

**The half of this that lives in `docs/FINDINGS.md` could not be anchored at all**, and that is
its own entry below rather than a note here. The half that can be anchored is `TASKS.md`'s; the
other is corrected in place with its prior wording kept.

*Site:* `TASKS.md` :: `> It is 25x. The prior wording stays per doctrine rule 4 and the delta is the finding: **a`
*Disposition:* the cross-reference is corrected on `evals/the-digest-cannot-tell-collect-from-window-mean`
along with `T00K`'s `closes`; **the entry is left open** because what it records is not the two
sentences — those are fixed here — but that nothing checks a cross-reference between two documents
in this repository, and there is no gate proposed for it
*Status:* open

**The register cannot anchor a finding about itself** · found 2026-09-02 · **recorded first by the
session that wrote `One anchoring rule, two populations`, as a parenthetical**, then met again from
scratch by T00L four hours later
**Attribution corrected before anything else, because getting it wrong here would be the finding
happening a third time.** This entry first read *found by T00L, by trying it*. It was recorded
hours earlier, on `main`, inside another entry: *"(And the rule cannot anchor to itself. A
`*Site:*` naming `docs/FINDINGS.md` quotes the fragment on the site line, which is then a second
occurrence in the same file …)"*. T00L met it fresh and paid the full cost — three attempts and a
correction — **and the session that had recorded it hit it again on its own branch the same day.**

> **The evidence for this limit is not only that it fires. It is that it fired on somebody who had
> already written it down.**

That is why it is filed as a limit in its own right rather than left where it was: **a limit
recorded inside another finding is not a limit anybody searches for.** It is one instance of
*Write discipline, and no read discipline* below, which is the general form.

**A limit of the instrument, in the register of language this repository's other limits use.** A
finding declares a `*Site:*` whose fragment must occur **exactly once** in the file it names. When
the file named is `docs/FINDINGS.md`, **the `*Site:*` line is itself a second occurrence of the
line it points at.** The rule then refuses the anchor — correctly, by its own terms, and
permanently.

**Measured, not reasoned.** Writing the cross-reference finding above, the anchor was tried and
`make findings` reported `AMBIGUOUS  the anchor occurs 3 times`; after the quoted sentence was
corrected it reported **2**, which is the floor: the defect line and the `*Site:*` line naming it.
It never reaches 1.

**Why this matters more than a quirk.** A defect *in the register* disarms every finding the
register carries, so it is the class most worth catching — and it is the one class the register
structurally cannot hold. **Every other instrument here has been hardened against exactly this
shape**: `ops/figures.py` raises rather than returning a smaller number, a `DEPENDS_ON` entry
naming nothing raises rather than being skipped, `gather` refuses a partial set rather than
averaging it. This one has the property inverted — it cannot examine itself — and it took writing
a finding about it to find that out.

**What made this one findable does not generalise.** It had a second half living in `TASKS.md`, so
the entry above anchors there. **A defect purely internal to `docs/FINDINGS.md` has nowhere to
go.**

**No fix is proposed, and the reason is the rule's own load-bearing property.** Both escapes
weaken it:

- *exclude the `*Site:*` line from its own count* — a rule that can be told to ignore one
  occurrence can be told to ignore the wrong one, and which occurrence is "its own" is a judgment
  the parser would have to make;
- *anchor by digest rather than by quoted text* — this discards the property the whole mechanism
  rests on, that **a moved line breaks its anchor**. An anchor that survives the line moving is not
  an anchor.

**And the cost, which is the honest half:** while this stands, **the register's own defects are
found by somebody noticing, not by `make findings`.** Today that was a session mid-edit, by
accident, while writing about something else.

*Site:* `ops/findings.py` :: `* a site whose fragment does **not occur exactly once** in the file it names. Zero means the line`
*Disposition:* **none — and stated as a limit rather than as work.** Neither escape above is worth
its cost, and a third has not been found. It closes if somebody finds a way to let the register
examine itself **without** teaching the anchor rule to ignore an occurrence or to survive a move.
Recorded so the next session that hits `AMBIGUOUS` on a finding about this file knows in one search
that it is the instrument and not their entry
*Status:* open

**Write discipline, and no read discipline** · found 2026-09-02 · by `projects-0a`, from four
instances in one day — three of them its own or T00L's
**Four things were correct, written down, and not found.**
**Every mechanism in this repository verifies that something is *recorded*. Nothing verifies that a
recorded thing is *retrievable*.** Anchors, restatement, dispositions, `*Now:*` lines, the refusal
of silence, `make expiry`, `make findings`, `make figures` — each one asks *was this written down,
and is it still true*. **None asks whether anybody can find it.** Every gate here would pass on a
register nobody can retrieve anything from.

**Four instances, one day, and all four were correct when written:**

| | what was written | what happened |
|---|---|---|
| 1 | the `TIMEOUT_SECONDS` entry's *"which is T00K's territory"* | followed by nobody; **two sessions designed against it for two hours** without opening `TASKS.md`, where T00K is *Shard claim 2's mutations* and cannot fix that flake at all |
| 2 | *the rule cannot anchor to itself*, a parenthetical inside another finding | **rediscovered from scratch four hours later at full cost**, and hit again by the session that wrote it |
| 3 | `CLAUDE.md` withdrawing the *100 stores* figure on 2026-08-29 | `TASKS.md` went on carrying it |
| 4 | `TASKS.md`'s heading: *Phase 2 — … (local)* | **the author was told for three days that phase 2 was Terraform and AWS**, by a session that had never opened the file |

**Three of the four were caught by somebody noticing mid-edit. The fourth ran for three days into
what the author was told.** That is the cost, and it is the honest half: **the register's
retrievability is currently enforced by attention.**

**It is the same shape as the write-side hole `T00G` closed**, one layer out: it fails safe on the
side that is checked, so nothing goes red. A cross-reference that is correct and unfollowed, a
limit that is recorded and unsearchable, a withdrawal that is published and uncarried — none of
them is a *defect* by any gate's definition, and all four cost real work.

**And this reaches the thesis rather than the housekeeping.** This project's claim is that a number
nobody can check is worth nothing. **A methodology that is correct and unretrievable is worth what
an uplift number without a holdout is worth** — the reader cannot get to the thing that would let
them check. That is the reason this is filed against the project and not against tidiness.

**No gate is proposed, deliberately.** Nobody here knows what would check retrievability, and a
mechanism invented in the same hour as the finding is exactly how the four confident sentences
above got written. The instances stay recorded and the general form stays unnamed until somebody
has a mechanism that is not a fifth confident sentence.

**RESTATED 2026-09-03 — a fifth instance, and it is not a fifth of the same thing.** The route-2
ruling removed `Lakeflow Connect` from `CLAUDE.md` at eleven sites. **`projects-0a` had written to
a build session, an hour earlier, that the method is to grep the name of the thing being *deleted*
rather than the names of the things it touches** — and then scoped its own sweep to `CLAUDE.md`.
Three present-tense mentions stood in `corpus/world/README.md`, `corpus/world/__init__.py` and
`corpus/world/chain.py`, describing a connector that had stopped existing the day before. They
were found by the next build session reading its own task's neighbours, not by a gate and not by
the sweep that was meant to be exhaustive.

**And a sixth, on the same day and from the same sweep, which is sharper than the fifth.**
`PLAN.md`'s phase-2 bullet opened *"the Zerobus driver that writes as the corpus's 100 stores
would"* — the figure `CLAUDE.md` withdrew on 2026-08-29 and `TASKS.md` restated for this very task.
**`#47` rewrote the line immediately below it** and left that one standing. So this is not a site a
sweep failed to reach: **it is a sentence its author edited, with the defect two lines above the
words being typed.** Found by the same build session, in the same reading.

**The four above are sentences that were written and not read. The fifth is a method that was
written, sent to somebody else, and not applied by its author in the next message** — so
retrievability was not the failure. The fact was retrieved, restated, transmitted, and still not
used. **A countermeasure that its own author does not apply is weaker evidence for the general
form than any of the four, and stronger evidence that no gate here is watching.**

*Site:* `TASKS.md` :: `## Phase 2 — pipelines, the metric contract's three consumers, the model (local)`
*Site:* `CLAUDE.md` :: `> are not measurements. It is withdrawn rather than corrected: **1,200 stores is the scenario the`
*Site:* `ops/findings.py` :: `* a site whose fragment does **not occur exactly once** in the file it names. Zero means the line`
*Disposition:* **none — and it is not work.** It closes when somebody proposes a mechanism for
retrievability that survives the objection above, or when the author decides the cost of attention
is acceptable and says so. Both are decisions. The child entry
*The register cannot anchor a finding about itself* is one instance of it and says so
*Status:* open

---

**A branch's warm caches do not survive its own merge** · found 2026-09-02 · by the first `ci`
run on `main` after `#41`, taken to check something else

`#41`'s last four runs on the branch were warm and claim 2 came in at **1701s** against an
unsharded median of 3271s. The first run on `main` carrying the same code, run `33600284036`,
took **4075s — 68 minutes**, and its combine job says why in its own log:

    Cache not found for input keys: worlds-Linux-d5d27bdca303d9be70f3b07057bee8a7-combine
    …
    Cache saved with key: worlds-Linux-d5d27bdca303d9be70f3b07057bee8a7-combine

**Same digest, same key, written by the branch four times, and `main` missed it.** The shards
tell the same story from the other side: 655 · 815 · 827 · 834 · 953 · 955 · 959 · 961 against
186–266 warm on the branch.

**Which half of this is measured.** That a cache written on the branch was not visible to `main`
— measured, above. That `main`'s caches *are* visible to branches, which is what makes this a
one-time transition cost rather than a permanent tax — **not measured here.** It is documented
GitHub behaviour and it is stated as documentation, because the whole weight of the "one-time"
reading rests on it and this repository has been wrong before about a fact it read rather than
ran.

**Nobody costed it, and it changes how one of the branch's own figures should be read.**
*Sharding pays — 1701s against a 3271s median* was measured in a cache state that the merge
destroyed. Neither figure is wrong: 1701s is the warm steady state and 4075s is the first run in
the code's permanent home. What was missing is the sentence naming which state each was taken
in, and that a branch which warms its caches over five runs hands `main` nothing.

**And a fourth observation of the rounding mutation fell out of the same run: 806s, 90%.**
`528 · 747 · 806 · 826` — **1.53x across four, none over 900.** It landed inside the first three
rather than beyond them, so the range holds and the trend stays dead. Nobody went looking for
it; it printed because the seconds print unconditionally, which was the argument for printing
them on green runs.

*Site:* `.github/workflows/ci.yml` :: `key: worlds-${{ runner.os }}-${{ steps.worlds.outputs.digest }}-combine`
*Site:* `evals/gate_proof/engine.py` :: `#:     528s (59%) · 747s (83%) · 806s (90%) · 826s (92%)     1.53x across four, none over 900`
*Disposition:* none — there is nothing to fix. A cache that has to be built once in the place it
will live is the cost of having caches at all, and the alternative is warming `main` on purpose,
which is a scheduled job spending runner time to make one number look better. It is recorded so
that a later reading of *sharding pays* knows which cache state produced it
*Status:* open

**An unlock condition points at a task whose `closes` does not mention it** · found 2026-09-02 ·
by reading T009 before starting it, because a peer's scoping did not match the layout

`docs/DECISIONS.md` defers `corpus/world/` writing gzipped CSV rather than Parquet, and its
unlock condition names a task:

    *Unlock condition:* the S3 bulk load in T009, which is the first thing that needs files on
    disk in the format the lakehouse reads. The writer gains a Parquet target there, beside the
    CSV one.

**T009's `closes` does not mention the S3 bulk load.** It names the driver and the Lakeflow
Connect definitions and stops. `CLAUDE.md`'s layout lists three things under `pipelines/ingest/`
and the bulk load is the third, so two documents assign it to that task and the task's own
`closes` omits it.

**The failure mode is silence, and it is the one this repository is worst at seeing.** T009
reached its `stop_at` honestly, closed, and the deferral would sit open pointing at a task that
finished without doing the thing it was waiting for. Nothing anywhere goes red: `make expiry`
checks that an unlock condition is **present**, never that it is **right** — the standing limit
`docs/DECISIONS.md` declares about itself and the one `CLAUDE.md` says is the smallest it can be
kept.

> **An unlock condition can point at a task whose `closes` does not mention the thing it is
> waiting for, and nothing checks that pair.**

**It is not `pricing/selection.py`'s shape and the difference is worth stating.** That one is
work named nowhere, assigned to nobody — an omission that announces itself the moment somebody
looks for an owner. This is work *with* a task, *with* something depending on it, and a summary
of that task that leaves it out. **The artefact looks complete**, which is the more dangerous of
the two shapes and the one `CLAUDE.md` already records under *a form the schema manufactured*.

**Fixed for this instance, not for the class.** `TASKS.md`'s T009 is restated per doctrine rule 4
— prior wording kept, the bulk load and the Parquet target named, `branch` widened to `branches`,
`stop_at` extended. **What is not built is the check**: nothing pairs an unlock condition that
names a task id against that task's `closes`, and the population is small enough to make it
plausible and awkward enough that it is a decision — an unlock condition is free prose by
design, and a checker over it would be reading English for meaning.

*Site:* `docs/DECISIONS.md` :: `*Unlock condition:* the S3 bulk load in T009, which is the first thing that needs files on disk in`
*Site:* `TASKS.md` :: `RESTATED 2026-09-02, because `closes` was incomplete and two other documents said`
*Disposition:* none for the class — the instance is closed by the restatement in the same change.
The check that would catch the next one is a decision about whether an unlock condition stays free
prose, which is the author's rather than a session's
*Status:* open

---

**A task note repeated a figure `CLAUDE.md` had withdrawn** · found 2026-09-02 · while reading
T009 for the same branch

T009's `closes` opens *"A driver that writes as the corpus's **100 stores** would"*. `CLAUDE.md`
withdrew that figure on 2026-08-29: 100 is the `scenario` scale, claim 2 runs at `harness`, and
the restatement's own subject is that a nominal store count is not the number anything rests on —
the surviving roster is. The paragraph making that argument **had the nominal number wrong
itself**, which is why the withdrawal is emphatic.

**The withdrawal did not travel.** `CLAUDE.md` restated; `TASKS.md` kept the number, in a task
that had not started, where the next session to open it would read *100 stores* as the
specification. It is the same shape as T008's note naming `G10` where `O2` was the correct check
— **a summary repeating a superseded figure is how a restatement fails to arrive**, and doctrine
rule 4 keeps the old value recoverable precisely so this is a correction rather than an
archaeology problem.

Restated in place with the prior wording kept. **What is not fixed is that nothing enumerates
where a withdrawn figure was copied to**, and the honest note is that both instances were found
by reading rather than by any gate.

*Site:* `TASKS.md` :: `And `100 stores` is a figure `CLAUDE.md` withdrew on 2026-08-29: 100 is the`
*Disposition:* none — the instance is corrected in the same change; the class is *a figure
restated in one file and repeated in another*, which is `make figures`' `PROSE` question over a
population nobody has enumerated
*Status:* open

---

**Nothing checks that a directory declared *not yet built* is still unbuilt** · found 2026-09-02 ·
by asking what T009 would do to the layout gate before writing anything

`CLAUDE.md`'s layout has two halves — what exists, and *"Declared and not yet built — phase 2 and
later"*. `ops/figures.py` asks two questions of them and there is a third it does not ask:

    is everything that exists named          layout_packages vs layout_packages_named  — asked
    is everything named real                 layout_fabrications, present block only    — asked
    is everything declared-future still future                                          — not asked

`layout_packages_named` searches the **whole** body, future block included, so a directory listed
under *declared and not yet built* satisfies it. The moment `pipelines/ingest/` exists, the map
describes it as unbuilt, the row stays green at `21 = 21`, and nothing anywhere says the sentence
became false.

**This is the third direction of a question this repository has already asked twice**, and
`CLAUDE.md` records the pair under *Three one-directional checks*: *is everything real listed* and
*is everything listed real*. The third is *is everything declared-future still unbuilt*, and it is
the one that goes wrong by ordinary work rather than by a mistake — every phase-2 and phase-3 task
moves a directory across that line.

*Site:* `ops/figures.py` :: `def layout_packages_named() -> int:`
*Site:* `CLAUDE.md` :: `**Declared and not yet built — phase 2 and later.**`
*Disposition:* none — the check is small and the edit it would force is to `CLAUDE.md`, which is
the author's. Filed so the first branch that creates one of those directories does not have to
rediscover that no gate noticed
*Status:* open

> **Restated 2026-09-03 by `pipelines/silver`, which is the crossing this entry was filed
> against — and it is the second, not the first.** `pipelines/ingest/` was created by `#45` on
> 2026-09-02 and has been listed under *"Declared and not yet built"* ever since; `T010` now adds
> `pipelines/silver/`. **Of the six entries in that block, two are built and the block says none
> of them is**, and the row stayed green at `22 = 22` through both, exactly as predicted.
>
> **The prediction was forward-only, which is the part worth keeping.** *"Filed so the first
> branch that creates one of those directories does not have to rediscover that no gate
> noticed"* was written on the day after the first branch had already landed: the entry looked
> ahead for a crossing that had happened the day before. A population enumerated in one
> direction, in a finding about a check that enumerates in one direction — and the entry's own
> author is not the one who noticed, which is the only reason it is recorded rather than argued.
>
> **`#47` then edited a line inside that block**, changing what `pipelines/ingest/` is described
> as doing, on a branch rebased onto a `main` that already contained the directory. The heading
> above the edited line was false about the line being edited.
>
> Both `CLAUDE.md` edits are the author's and are with him.
>
> **Restated again 2026-09-03: the edits have landed, and the entry does not close with them.**
> The author delegated both to the integration session. `pipelines/ingest/` and `pipelines/silver/`
> are in the built map, and the engine row names what the OSS framework actually has. **Two
> instances were corrected by hand and no check was added** — which is the thing this entry has
> asked for since it was filed. What changed is the state it described, not the gate. It stays open.
>
> **And the anchor survived the edit for a reason worth recording.** This entry's `*Site:*` quotes
> the block's **heading**, not a line inside it, so moving two directories out of the block did not
> move it. An entry anchored to the contents would have gone red on the very change that resolved
> its instances, and would have had to be restated under a red gate. **That was luck rather than
> design when it was written**, and it is the argument for anchoring a finding about a container to
> the container rather than to what is in it.

**The mutation budget was a lottery that had not been drawn, and then it was** · found
2026-09-02 · by run `33610996234`, ninety minutes after a branch asserted it had never been
crossed

`the-grouped-path-rounds-like-a-price-not-like-the-contract` was killed at its 900s budget on
`docs/day-one`, turning a run red on a tree whose gates were all working. Read from six job logs
rather than from any summary:

    528s (59%)   33584456101      747s (83%)   33577549272      779s (87%)   33615045192
    806s (90%)   33600284036      826s (92%)   33581480860      847s (94%)   33608418765
    >=900s       33610996234  — CRASHED, killed at the budget

**Six completed, one killed.** The completed span **1.604x**, and the budget sat **1.063x** above
the highest of them.

> **A limit 1.06x above the highest observation of a quantity that varies 1.60x is not a limit.
> It is a lottery that had not yet been drawn.**

**And the killed run measures the budget, not the work.** Its true cost is unknown and above 900,
so the distribution has six points and one **censored** observation — which is claim 4's own
subject arriving in this repository's instrumentation, and the reason no value derived from what
completed can be shown to cover it.

**What makes this entry rather than an edit is when it happened.** `#42` was written from four
observations and states in `engine.py` *1.53x across four, **none over 900***. Ninety minutes
later the repository disproved it. The line stays, per doctrine rule 4, with the full table under
it: **the most recent observation table in that file was the thing that stopped being true**, and
that is a better record than a silently corrected number. A later reader trusts the newest table;
this one now carries its own refutation.

**One correction to how this was assembled, which is the method rather than the finding.** The
set was given to me as *five completed, spread 1.56x, margin 1.09x*. Pulled from the job logs it
is **six** — the sixth, 847s at 94%, was on this very branch's own run and had not been read by
either session. Spread 1.604x, margin 1.063x. **The corrected numbers make the argument stronger,
which is the only reason it is safe to report that they were corrected at all.**

**And a raise was drafted, checked, and withdrawn — which is the other half of the finding.**
An interim of 1359s was written: 847 x (847/528), the highest completed observation times the
spread the completed ones show. Both inputs measured, **the rule combining them chosen** — the
draft called it *every factor measured, none chosen*, which is precisely what 900 was and what
the sentence hid.

It did not survive its own headroom check. `gate_proof --claim 2` runs in **`claim-2-combine`,
ceiling 60 minutes**, and that job's worst measured run is 2824s: cold `--combine` 1339s, the
baseline and seven cheap mutations 671s, `07` 806s. Component-wise worst with `07` at 1359 is
**1339 + 739 + 1359 = 3437s against 3600 — a margin of 1.047x**, on a job whose nine measured
runs span **2.88x**. Tighter than the 1.063x this same entry calls a lottery.

**So the raise would have moved the failure rather than removed it**: from a red that names the
mutation, prints `900s of a 900s budget (100%)` and lands on this entry, to *the combine job
timed out at 60 minutes*, which names nothing and kills whatever else was running. A budget that
fits the ceiling with the margin `claims` was given (1.15x) would cap `07` near 1052s — 1.24x
above its highest observation of a quantity varying 1.604x, a lottery on the other side.

*Site:* `evals/gate_proof/engine.py` :: `#: > **A limit 1.06x above the highest observation of a quantity that varies 1.60x is not a`
*Site:* `evals/gate_proof/engine.py` :: `#: is safe while the combine's ceiling is 60 minutes.** Both move together or neither does, and`
*Disposition:* none — **no per-mutation value is safe while the combine's ceiling is 60 minutes.
Both move together or neither does.** Nothing is changed here and `TIMEOUT_SECONDS` stays at 900:
every observation is of the mutation in its expensive form, the change that stops it paying for a
regeneration it is not testing removes that form, and a number set now is set from a distribution
about to stop existing. Not `T00K`, which shards the mutations and leaves each one's own cost
exactly where it was. It closes when that change has landed and `07` has been re-measured in the
form it leaves behind — both halves, because the first alone is a condition naming a task
*Status:* open

**Two ceilings wrong in opposite directions, and the split that did it was ours** · found
2026-09-02 · by checking whether a raise would fit, and finding the other ceiling in the same file

`ci.yml` carries two budgets that were each measured honestly and are now wrong in **opposite**
directions, and one change made both of them wrong: the sharding that moved claim 2's work out
from under them.

    claims   timeout-minutes: 90    justified from 71 jobs, cold max 78.3 min, spread 2.43x
                                    — of claim 2 running WHOLE in that job, which it no longer does
    combine  timeout-minutes: 60    where the mutations went, and where 900 was already too tight

**What runs under `claims` now, measured over nine runs:** the worst single job is
`claim-2 tests` at **1235s — 20.6 minutes**, on the cold post-merge run; then `claim-1` at
653–715s and the shards at 147–973s. **A 90-minute ceiling against a 20.6-minute worst is a
margin of 4.4x**, and a job wedged for an hour and a quarter would sit there burning budget with
nothing to stop it. **A ceiling that cannot fire is not a safeguard.**

So: **900 is too tight to survive the work it bounds, and 90 is too loose to bound anything.**
Both were right when written. Neither was re-derived when the work moved.

> **A number is justified by a measurement of the work it bounds. When the work moves, the
> justification does not move with it — and nothing in this repository notices, because a
> ceiling nobody reaches and a ceiling reached at random both look like green runs until one of
> them does not.**

**It is one finding and not two**, and that is the whole of it: the same change produced both,
and a session correcting either one alone would set it from a distribution the other is about to
change again.

**And the figure that opened this was wrong in the safe direction.** It was put to me as *12
minutes against 90, a margin of 7.5x*, computed from `claim-1` and `claim-3` alone — the eight
shards and `claim-2 tests` run in the same matrix under the same ceiling. Measured, it is 20.6
minutes and 4.4x. Weaker than claimed, still far too loose, and re-derived rather than taken.

*Site:* `.github/workflows/ci.yml` :: `    timeout-minutes: 90`
*Site:* `.github/workflows/ci.yml` :: `    timeout-minutes: 60`
*Disposition:* none, and deliberately not fixed here. This branch already carries the argument
for changing none of the three numbers, and the lesson is that ceilings get derived after the
work settles rather than during a change that moves it. All three come together once the mutation
stops paying for a regeneration it is not testing and `07` has been re-measured
*Status:* open

---

**Resolving a `docs/FINDINGS.md` conflict can drop an entry's `*Status:*` and nothing says so** ·
found 2026-09-02 · while rebasing this branch onto `#43`

Two branches added entries at the same place — immediately before `## Closed` — and git produced
one conflict hunk. **The `*Status:* open` line of the last entry sat *outside* the markers**,
after `>>>>>>>`, because both sides ended with a `*Disposition:*` and the line after was common
text.

**So the obvious resolution is wrong in a way that reads as right.** Keep both hunks, delete the
three markers, and the first block's last entry has **no `*Status:*`** — it inherits nothing,
because the shared line now closes the second block instead. The diff looks like a clean union.
`ops/findings.py` would report the entry as adrift or drop it from its counts, and the register
would be quietly one entry short of what two people believed they had filed.

**This is the register's own failure mode arriving through git's mechanics rather than through
anyone's judgment**, which is why it is filed rather than fixed in passing: nothing about it is a
defect in `findings.py`, and no rule about how to *write* entries would have prevented it.

Two things make it likely rather than exotic. Entries are appended at one point in the file, so
**every pair of branches that files a finding conflicts there** — this repository now files
several a day. And the fields are ordered so that `*Status:*` is last, which puts the line most
likely to fall outside the hunk on the field whose absence is hardest to see.

**What was actually done here**, so the next resolution has a procedure rather than a warning:
union in landing order, `main`'s entries first; add the missing `*Status:*` to the block that
lost it; re-run `make findings` **before** committing, because it is the only thing that can see
the difference.

**And the `*Site:*` below names `ops/findings.py` rather than this file, which is not a
preference.** A finding about `docs/FINDINGS.md` cannot anchor to `docs/FINDINGS.md`: the site
line is itself a second occurrence of the fragment it quotes, so the gate reports `AMBIGUOUS`
and never `1`. That limit is recorded a few entries above, as a parenthetical inside *One
anchoring rule, two populations* — found by trying it and going red. **It has now been hit twice
in one day by two sessions**, which is what a parenthetical buys: the second session met it
fresh, because a limit recorded inside another finding is not a limit anybody searches for. It
is being filed as an instrument limit in its own right elsewhere and is deliberately not filed
twice here.

This entry survives it only because it has a half that lives in another file — the regex that
would fail to see the missing status. **A hazard with no such half could not be anchored at
all**, and the honest move there is to say so in the entry rather than to invent an anchor that
satisfies the checker without naming the defect.

> **It fired a second time on 2026-09-05, on `#59` against `#60`, and the procedure above is
> what resolved it.** Same place, same shape: one hunk, both sides ending on a `*Disposition:*`,
> and the `*Status:* open` sitting after `>>>>>>>` as common text. Union in landing order —
> `main`'s two entries from `#59` first, then the phase-2 review's sixteen — with a `*Status:*`
> added to the block that would have lost it.
>
> **And the check gained an arithmetic that this entry did not have.** The integration session
> asked for the count of `*Disposition:*` and `*Status:*` lines **before and after**, with the
> gap between them required not to move: 88/85 on one side and 74/71 on the other, both a gap of
> three, and 90/87 after — the same gap, and `ops/findings.py` parsing 90 entries where 88 + 2
> were filed. **A pair of counts either side of the resolution catches the silent case that a
> single count after it cannot**, because a block that lost its status still parses and still
> prints; it prints as one entry fewer, against a total nobody wrote down.
>
> Recorded as a second instance rather than as a new finding: nothing about the hazard changed,
> and the only new thing is that the written procedure worked when somebody who had not written
> it followed it.

*Site:* `ops/findings.py` :: `_STATUS = re.compile(r"^\*Status:\*[ \t]*(?P<what>open|concurred)[ \t]*$", re.MULTILINE)`
*Disposition:* none — a `.gitattributes` union driver would make it worse rather than better,
because union is right for disjoint entries and wrong for two branches restating the same site,
and nothing mechanical can tell those apart. The procedure above is the mitigation and
`make findings` is the check
*Status:* open

**The cold-combine figure justifying a CI job does not match the job, or itself** · found
2026-09-02 · by T00L measuring where its own 37 minutes went, and by `projects-0a` reading the
comment against it
`ci.yml`'s `combine` job carries a comment explaining why a ten-minute penalty is cached rather
than removed:

> *"Measured on this repository's corpus: a cold combine is **596s** against 1s warm, of which
> `_truths` — the counterfactual generations, which no draw shard produces — is **411s**, `U11`
> **195s** and `U10` **51s**."*

**Two things are wrong with it and they are independent.**

**First, it does not agree with itself.** `411 + 195 + 51 = ` **657s**, against a declared total of
**596s** — **61s over**. Whatever the parts are, they cannot be parts of that whole, so at least
one of the four numbers was taken at a different moment from the others and they are presented as
one decomposition. **This needs no comparison with anything to be a defect**, and it is visible in
the comment as written.

**Second, it does not agree with the job.** Measured on run 33621267184, `make claim-2-combine` is
**2229s**, of which the eval's `--combine` phase is **1432s** — and that run *was* cold, because
T00L changed two files in `evals/uplift/cache.py`'s `DEPENDS_ON` and moved the digest. **1432s
against a recorded 596s is 2.4x.**

**Two readings, and neither is chosen here because neither has been checked:**

- **the corpus grew and nobody re-measured** — the figure was true and went stale;
- **596s is a laptop number in a comment about runner behaviour** — which is `CLAUDE.md`'s rule that
  *where a number will be met on hardware that is not the author's, the measurement is taken there*,
  and it would be the **third** time this repository has hit that shape in one direction. `T00H`'s
  entry records the laptop nearly making the same error about which half to shard, and `ci.yml`'s
  own `timeout-minutes: 45` was a fourteen-core projection onto a four-core runner.

**Why it matters more than a stale comment, and this is the operative half.** Anybody opening the
23m52s that `--combine` now costs would start from the itemisation: *`_truths` is 411 of 596, so
attack `_truths`.* **That share is currently unverifiable.** If `_truths` is 411s of **1432s** it is
**29%**, not 69%, and the obvious target is the wrong one — a twenty-minute optimisation aimed by a
number nobody has re-taken.

**So the re-measurement is the work, and it comes before any proposal about what to remove.** No
proposal is made here.

**And there is a structural point that says where a re-measurement should start — it is not a
third reading.** The comment's prose says the job *"carries a **ten-minute** cold penalty"*, and
**596s is 9.93 minutes**. Prose and total agree with each other; **only the itemisation disagrees
with both.** Three of the four numbers tell one consistent story.

That does **not** discriminate between the two readings above — a larger corpus and a slower
machine both make items exceed an older total, in the same direction. **What it does say is which
number to distrust first**, and therefore where the cheap work is: **re-measure the itemisation,
not the total.** If `_truths`, `U11` and `U10` come back summing to at or under a re-measured
whole, the total was merely stale; if they come back in the same proportions against a much larger
whole, the comment was assembled from two sittings and presented as one.

*Site:* `.github/workflows/ci.yml` :: `  # Measured on this repository's corpus: a cold combine is 596s against 1s warm, of which`
*Disposition:* its own branch, unlocked now — the measurement needs only a run with the four
phases timed, and `T00K` should not be opened against the 23m52s until it exists, because `T00K`'s
own value is already the smaller of two numbers and the larger one is the one in question. **Not
folded into T00L**: that branch is finished work about a cache digest, and this is a figure in a
workflow comment
*Status:* open

---

**The layout block cannot say *declared and never to be built*** · found 2026-09-02 · by asking
what the ruling does to the repository map, before writing anything into it

`CLAUDE.md`'s layout has two halves — what exists, and *"Declared and not yet built — phase 2 and
later"* — and the paragraph above the second one gives the rule it enforces: *a directory that
does not exist may not be described in the present tense beside directories that do.*

**`infra/sources/` was correctly in the second half until today.** The route-2 ruling closes
`T019` as *not built, and here is why*, so that directory is no longer *not yet* built. It is
**never** going to be built, and the block has two states for a thing that now has three.

The author's edit takes `sources` out of the `infra/` line and the reason lives in
`docs/DECISIONS.md`, which is the right size of fix: a third marking on the file every session
reads first, made on the day a ruling lands, is more than a ruling needs. **What is not fixed is
that the block still cannot express the state**, and the next withdrawal will meet the same
absence.

**It is the second direction of a question `#42` files the first half of.** That branch records
*is everything declared-future still unbuilt* — a directory that got built while the map still
calls it future. This is *is everything declared-future ever going to be built* — one that will
never arrive while the map still promises it. **Neither is checked**, and they belong beside each
other; `#42` is open at the time of writing, so they are two entries until it lands.

**And the site was reachable by one method only.** It says none of *Lakeflow*, *RDS* or
*Postgres*. It says `sources`, the name of the layer being deleted — so no grep for the things
the change was *about* reaches it. **Grep the name of the thing being removed, not the names of
the things it touches**, which is a method rather than a piece of luck and should run on every
future deletion of a named thing.

**Re-anchored 2026-09-05 by `ops/a-published-figure-is-read-off-its-measurement`, and the move is
itself the third instance.** The site was the `infra/` line in the *declared and not yet built*
block. That branch moved `infra/` **out** of the block — it was built on 2026-09-04 and the block
was describing a built directory as unbuilt — so the anchor is gone and `make findings` reported
`MOVED` rather than passing quietly, which is the gate doing its job on a line nobody remembered
was load-bearing twice.

**The finding is not closed by that move and the class is untouched.** The block still has two
states for a thing that has three, and it now has a fourth thing to say — *built, and here is
which part of it* — which is what the `infra/` line in the block above had to be written as. The
site is restated to **`experiments/`, the block's one surviving entry** — not to the paragraph
stating the rule, which was the first re-anchor and was wrong. **A rule's sentence will never
change, and an anchor that cannot move is a tripwire with nothing on it.** Anchored to
`experiments/`, the finding fires the day that directory is built and the block empties, which is
the moment its premise changes and the moment somebody has to decide what the block is for.

*Site:* `CLAUDE.md` :: `experiments/           one YAML per experiment, in git, with its full history`
*Disposition:* none — the instance is closed by the author's edit. The class is a third state the
layout block has no marking for, and adding one is a change to `CLAUDE.md`'s structure rather than
its content, which is his
*Status:* open

---

**Two stale summaries, recorded and unnamed** · found 2026-09-02 · both by re-deriving a count
that had been written once

Two instances of one mechanism on one day, **recorded as instances with no rule over them**,
which is what `CLAUDE.md` does with *Three one-directional checks* and for the reason it gives
there: a rule generalised early is scoped to the shapes its instances happened to wear.

- **`#43`'s gateway finding** said *"five of its seven sections stop applying"* of
  `docs/DAY-ONE.md`. Measured against the document, it is **six**. §2 survives, and its own text
  says why: the binding region constraint is Zerobus, whose availability list is the narrower one,
  so removing the connector's wider list changes nothing.
- **`#42`'s own pull-request title and body** said *four findings* while the branch carried
  **seven**, and the three omitted were the three with numbers in them. Corrected on the pull
  request; **it has no anchor in this tree, because a pull-request body is not a file**, and that
  is said here rather than an anchor being invented to satisfy the checker.

**The distinction to keep, because a third instance is what decides which rule gets written.** A
stale figure **inside a document** is wrong where a reader can check it against the thing it
describes. A stale summary in a **review surface** is wrong where the reader uses it *instead of*
the thing it describes — a pull-request body is, for most reviewers, a substitute for reading the
whole diff. Same mechanism, different blast radius, and the second is the one whose omissions a
reader cannot reconstruct.

*Site:* `docs/DAY-ONE.md` :: `**Zerobus is the narrower list, so the intersection is the Zerobus list**`
*Disposition:* none — deliberately unnamed at two. The moment is a third instance in a form
neither of these wears, at which point the distinction above decides between *re-derive counts*
and *re-derive counts on anything a reviewer reads in place of the artefact*
*Status:* open

---

**`*Now:* gone` is checked by nothing at all** · found 2026-09-02 · by nearly writing a false one
while closing the first two findings this register has ever closed

`docs/FINDINGS.md` checks two of its three anchor forms and not the third:

    *Site:*                  the fragment must occur in its file exactly once   — checked
    *Now:* `path` :: `text`  the replacement text must occur, exactly once       — checked
    *Now:* `path` :: gone    nothing                                             — NOT CHECKED

**A `gone` is an assertion of absence, and absence is the one thing this register never
verifies.** Write `gone` about a line still sitting in the file and `make findings` is green, the
entry reads as closed, and the register asserts a disappearance that did not happen.

**The evidence is a near-miss on this branch and it travels with the entry.** Closing the
PostgreSQL-connector finding, its second site — `docs/DECISIONS.md`'s `make preview-audit`
deferral — was written as `gone — the deferral it anchored to is restated on this branch`. **It is
not gone.** That deferral unlocks at *the first time a preview surface is considered*; route 2
removes a surface, not the condition. The line is untouched in the file. It would have passed.

**Why this is filed rather than recorded as one instance under the usual restraint.** *Record
instances, name no rule* governs a pattern waiting for a third example to show its shape. This is
not a pattern — it is a proven hole in a named mechanism, and `TASKS.md` already carries the rule
for that case, from `T00G`:

> **A proven silent hole may not be declared as a limit by the branch claiming its coverage is
> computed.**

**This is that branch.** It is the branch closing findings by `*Now:*`, and it found that one of
the three forms it relies on is unchecked. Declaring it as a limit here and moving on would be the
exact shape `T00G` refuses.

**It is under-coverage rather than over**, which is the direction `ops/figures.py` calls the lie:
a gate that cannot fail on a false claim of absence reports on what it examined as though that
were what exists.

*Site:* `ops/findings.py` :: `_NOW = re.compile(`
*Disposition:* none, and **no gate is proposed here** — the same restraint, for the same reason
the entry above it gives. What a checker would have to do is decide what *absence* means for a
line that may have been reworded rather than removed, which is a judgment about the register's
own grammar rather than an edit
*Status:* open

---

**A source enumerated by a glob carried the injected corpus's own tables into bronze** · found
2026-09-03 · by running the bulk load rather than by reading it

`pipelines/ingest/bulk.py`'s first version took its history sources as *every `*.parquet` in the
landing area*. `corpus/world/`'s Parquet target writes the three reference tables beside the four
event streams — **`store_master` among them, carrying the `arm` column the ERP export deliberately
withholds** — so the eight months of history registered the ERP's own tables into bronze by a
second route. **Twenty-two files loaded where nineteen was right**, and the extra three were the
three a downstream join could have taken a store's arm from instead of from the assignment written
before the period opened.

**The barrier that exists for this does not watch this direction.** `ops/isolation.py` polices
*imports*: no module under `corpus/` may reach the system. This was not an import. It was a
directory listing, in the other direction, from a pipeline into the corpus's own output — and the
same listing would have taken `truth.sealed.json` if the seal had been a `.parquet`.

**Fixed on the branch that found it**, by replacing the population rather than by filtering it: a
source is now **a file some manifest names** — each drop's `_manifest.json`, then each stream each
`run.json` counts. Nothing else is a source, an undeclared `.parquet` planted by hand is a test,
and the seal is declared by nothing at all.

**The generalisable half is a rule and not a patch**: *enumerate by declaration, never by glob.* A
glob answers *what is in this directory*, which is a question about a filesystem; every ingestion
path is asking *what did somebody hand me*, which is a question about a manifest. The two agree
until something else writes into the same directory, and then the difference is silent.

*Site:* `pipelines/ingest/bulk.py` :: `    for run_manifest in _history_manifests(landing):`
*Site:* `pipelines/ingest/erp.py` :: `WITHHELD: dict[str, tuple[str, ...]] = {"store_master": ("arm",)}`
*Disposition:* `pipelines/ingest-bulk-load` — the code is fixed there and the tests are
`test_the_seal_and_the_reference_tables_of_the_history_are_not_sources` and
`test_the_export_withholds_the_arm`. **Left open rather than closed by its own author**: closure is
a transition, and the transition here is that branch landing
*Status:* open

---

**The world-cache digest hashes a directory, and the dependency is a file** · found 2026-09-03 · by
adding a module to `corpus/world/` that cannot change a world

`evals/uplift/cache.py`'s `DEPENDS_ON` names `corpus/world`, and `_source_files` hashes **every**
`.py` under it. `corpus/world/parquet.py` is a file writer: nothing the A/A harness calls imports
it, and no world's data can differ because of it. Adding it invalidated every cached world anyway,
so `pipelines/ingest-bulk-load`'s CI run pays cold world generation in every claim-2 shard.

**This is `T00L` one level out, and nobody has written that the two are the same shape.** That task
closed *the digest hashes a file, and the dependency is a function* — a key too coarse **inside** a
file. This is a key too coarse **across** files: same defect, one granularity out, and the cost has
the same sign in both — spurious invalidation, never a stale world.

**No proposal, and that is deliberate.** The coarse key is the safe direction and it was chosen
knowingly: `_source_files` raises rather than returning a shorter list precisely because a digest
that misses a dependency reports `SURVIVED` for a mutation that never ran. Narrowing it to a
reasoned subset would put a judgment about which corpus modules can affect a world into the one
place this repository refuses to guess — and a branch narrowing claim 2's instrument for its own
convenience is the trade `T00G` refuses in the other direction. **What is filed is the instance and
its cost, not a fix.**

*Site:* `evals/uplift/cache.py` :: `    "corpus/world",`
*Disposition:* none — the key is deliberate, the cost is paid knowingly, and the entry exists so
that the next branch adding a file to `corpus/world/` reads the price before its CI run does
*Status:* open

---

**Four tests passed over an empty population, and reading them did not show it** · found
2026-09-03 · by planting an empty landing area, after the same defect had already appeared in a
verification of the same branch

`tests/pipelines/test_bulk_load.py` asserts things about what a load produced by iterating
`result.loaded` and by asserting negatives over the set of sources. **Four of those tests were
true of a landing area that held nothing**: a loop over an empty list checks nothing, a negative
over an empty set is satisfied, and *a second load moves nothing* is trivially true when the
first load moved nothing either. Every one of them read as a real assertion.

**It was found by planting, not by reading.** With `erp.export` replaced by a `mkdir`, nine of
the fourteen tests in that file go red; with the history removed as well, twelve do — and the
four in question are the difference between what the guards catch and what the assertions alone
did. They now state the population they examined, **as a rule and never as a frozen count**,
which is `ops/figures.py`'s doctrine applied one layer down: a count written into a test is an
assertion needing its own measurement, and it goes stale the day a dataclass gains a field.

**Third instance of one family, recorded and unnamed.** The tree already carries two, and both
are about an *instrument* rather than a comparison:

- `ops/figures.py` — *an instrument that cannot answer raises rather than returning a smaller
  number*;
- `evals/uplift/cache.py`'s `DEPENDS_ON` — an entry naming nothing **raises**, where it used to
  be skipped in silence.

This one is a **check reporting success over an empty population**, and it is the first where
nobody noticed by reading. **No rule is written over the three.** `CLAUDE.md`'s own precedent
governs — *a rule generalised at three instances is scoped to the shapes those three happened to
wear* — and these three wear an instrument, a dependency list and a test. The fourth, in a form
none of them wears, is the moment.

**And the instance that is not filed belongs in the same paragraph as the one that is.** The
branch's own verification that the CSV target is byte-identical first ran with store ids this
corpus does not use, so the restriction matched nothing, both sides generated an empty world,
and it reported **7 of 7 files identical over 35 data rows** — a green comparison of two
nothings, caught by reading the row count rather than the verdict. It has no `*Site:*` because it
is a scratch-directory comparison rather than a line in this tree, and inventing an anchor for it
would be worse than recording it here.

> **The failing shape and the vacuous shape print the same word.**

*Site:* `tests/pipelines/test_bulk_load.py` :: `    assert first.files > 0 and first.rows > 0`
*Site:* `tests/pipelines/test_bulk_load.py` :: `    assert examined == len(erp.EXPORTED) * len(erp.DECLARED.hours)`
*Site:* `tests/corpus/test_world_parquet.py` :: `    expected = sum(len(field_names(STREAM_TYPES[stream])) for stream in STREAMS)`
*Disposition:* `pipelines/ingest-bulk-load` — the four are guarded on that branch and the guards
are proved by planting. **Left open rather than closed by its own author**: closure is a
transition, and the transition is that branch landing
*Status:* open

---

**A drop's digest described the second it was written in** · found 2026-09-03 · by CI run
`33739596010`, on a test that had been green locally and on three earlier runs

`pipelines/ingest/erp.py` wrote each extract with `gzip.open`, **which stamps the current time
into the gzip header**. So exporting the same rows twice produced different bytes, and
`bulk.load` — correctly, by its own rule — refused the second as a path whose content had
changed:

    BulkLoadError: drop=000/store_master.csv.gz was loaded with digest 459e13a631a0
                   and now has 97a46722ae7f. A drop is immutable …

**Two exports inside one second are byte-identical; two a second apart are not.** On this laptop
they landed in the same second every time. On a slower runner they did not, and `make check`
went red on `tests/pipelines/test_bulk_load.py::test_the_load_log_records_every_file_and_never_rewrites_one`.

**It passed locally and on three earlier CI runs by timing**, which is worth stating in those
words: *three green runs* is exactly the evidence a reader would otherwise take as proof that
the code was fine. It was on `main` from `#49` and every branch's `make check` was exposed to it.

**The loader was right on every one of those runs.** What was wrong is that a drop's digest
described **when** it was written as well as **what** was in it. The fix is at the source rather
than in the test: the exporter writes with `mtime=0`, so the digest is a function of the content
and *a drop is immutable* is true by construction rather than by how fast the machine was.

**And the check written to verify the fix was itself wrong first.** It compared `a.gz` against
`b.gz` and reported that `mtime=0` also differed — because gzip writes the **basename** into the
header too, and the real scenario is one basename in two directories. Re-measured correctly:

    gzip.open,  same name, 1.1s apart:  64ff41fcabb9 vs acc429423d6d -> DIFFERENT
    mtime=0,    same name, 1.1s apart:  c41065fad480 vs c41065fad480 -> same

A comparison that varied two things and attributed the difference to one, inside the
verification of a timing defect. **It cost one command, because the result was implausible
enough to re-read** — which is not a gate and is the only thing that caught it.

*Site:* `pipelines/ingest/erp.py` :: `        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed,`
*Site:* `tests/pipelines/test_erp_drops.py` :: `def test_exporting_the_same_drop_twice_produces_the_same_bytes(tmp_path: Path) -> None:`
*Disposition:* `pipelines/a-drop-digest-is-its-content`, which is this branch — **split out of
`T010` deliberately**: the flake is on `main` and taxes every branch, and *we shipped a latent
flake and this is the fix* is a record that belongs in its own pull request rather than inside a
six-commit argument about Spark. **Left open rather than closed by its own author**
*Status:* open
**A mark cannot isolate an environment; only an import site can** · found 2026-09-03 · by CI,
on a branch whose author had run the full gate locally and seen it green

`T010` puts Spark in an optional dependency group so that **one CI job of twenty** installs 713
MB and a JVM. `make test` deselects `-m silver`; `make silver` and one workflow job run it.
**That arrangement was broken by a single import line**, and every machine a developer works on
is a machine where the break is invisible — because it is the machine that installed the extra.

    tests/pipelines/test_silver.py    import pyspark        (module scope)
    gate, run 33737357923             ModuleNotFoundError: No module named 'pyspark'
                                      at collection, `make check` Error 2

**pytest imports every test module before it applies a mark expression.** So a mark can decide
what *runs*; it cannot decide what is *imported*, and an environment can only be isolated at the
import site. The fix is that every engine import in that file now lives inside the function that
needs it — **which is not a skip and must not become one**: an absent engine still fails at the
first test that asks for it.

**Verified in the environment rather than reasoned about**, by removing the extra from the
worktree:

    uv sync --locked      pyspark absent
    make check            OK, all eight gates
    make silver           ModuleNotFoundError: No module named 'delta'
                          from pipelines/silver/session.py:27 — not a skip

**Same boundary, two directions, and only one was guarded.**
`tests/boundary/test_the_engine_is_never_skipped.py` was written **before** silver existed and
refuses `importorskip`, `skipif` and `skip` naming an engine — the **silent-green** direction,
which had a story behind it: an engine in an optional group is exactly where somebody reaches
for a skip. The failure came along the other axis — **loud red in a target that has nothing to
do with silver** — and nobody had imagined a failure there. **The incompleteness lay exactly
where there was no story**, which is `a guard tested by its author` with the author's
imagination as the population.

**Closed by the same tool, one more visitor.** The AST walk that already reads every `*.py`
under `tests/` now also refuses a **module-level** engine import, with `if TYPE_CHECKING:`
exempted because it never executes — the one module-level spelling that costs nothing at
collection, and the one silver's own tests use for their annotations. Proved by planting the
exact line CI caught and watching that file's parametrised case go red.

**And the class is wider than this repository's version of it.** `CLAUDE.md` records that a
number measured on the author's hardware must be re-measured where it will be met — cores, wall
clocks, timeouts. **Nobody had written the same rule for what is *installed*.** A laptop cannot
reproduce a runner's environment by being careful, because the laptop is the machine that
installs everything; `uv sync --locked` with no extra before pushing is a practice, and a gate
cannot make a laptop forget what it has.

*Site:* `tests/boundary/test_the_engine_is_never_skipped.py` :: `def imported_at_module_scope(source: str, filename: str) -> list[str]:`
*Site:* `pyproject.toml` :: `spark = [`
*Disposition:* `pipelines/silver` — the gate is on that branch and bites the line that caused
it. **Left open rather than closed by its own author**: closure is a transition, and the
transition is that branch landing
*Status:* open

---
**Silver read four of seven bronze tables and none of them carried the grain's third column** ·
found 2026-09-04 · by `T011` asking which silver table supplies `category`, before writing any
gold

Every metric contract declares `grain: [store_id, iso_week, category]`. `category` is a
`product_master` column. **`pipelines/silver/build.py`'s `BRONZE_TABLES` did not read
`product_master`**, so there was no silver table carrying it and **no gold table could have been
built at the grain its own contract declares.**

Measured rather than read off the code — a smoke W6 bronze through `erp.export`, `erp.history`
and `bulk.load`, 19 files and 38,168 rows:

    bronze holds   cost_ledger  esl_acks  pos_lines  price_decisions
                   product_master  shelf_days  store_master        7 tables
    silver read    pos_lines  esl_acks  shelf_days  cost_ledger     4 tables

**Two documents were already ahead of the code.** `CLAUDE.md` says `reference` *"collapses six
bronze tables into one as-of queryable dimension"*; `pipelines/silver/__init__.py` said it
*"collapses the ERP's tables"*. `tables.reference` took one argument and collapsed one table.
Same family as the six-worlds table and as W3's row — **a sentence describing a function that
does less than it says** — and it survived because nothing downstream of silver existed to need
the difference. `T010`'s own `stop_at` was *quarantine non-empty on planted bad data*, which four
tables satisfy as well as five.

**The half that is not a naming defect.** Putting the product columns in `reference` makes half
the dimension as-of and half of it not: `cost_ledger` publishes `effective_from` and the loader
stamps `known_from`, while `product_master` publishes **no time at all** —
`pipelines/ingest/erp.py` says so in as many words. So a product attribute is resolved by **key**,
and a change to one applies to all of history because there is no date to apply it from. That is
`CLAUDE.md`'s own *"joining to the current cost table silently rewrites every historical margin"*
arriving in a dimension that cannot avoid it, and it is written down rather than smoothed.

**And the second join earns its place by a number, not by an argument.** Resolving the product
columns through the as-of pick instead would be right on almost every row — a category is the
same on all of a sku's cost steps, so whichever step wins carries the right one — and wrong on
exactly the rows where **no step survives**. Measured on this corpus, both branches run:

    receipt lines with no cost known at the moment of the sale     1,418 of 35,695
    of those, lines that lose their category through one join      1,418
    of those, lines that lose their category through two joins         0

Through one join those 1,418 would have entered gold with a null in the `category` position of
every metric's declared grain, **and the number would still have been a number.**

**`store_master` and `price_decisions` are still unread**, and are named in `tables.reference`
rather than left to be discovered the same way. No metric's grain needs a store attribute and
`store_id` passes through the events unchanged; `price_decisions` is the corpus's analogue of
`gold.decisions`, which is family D and is not built.

*Site:* `pipelines/silver/tables.py` :: `def reference(cost_ledger: DataFrame, product_master: DataFrame) -> tuple[DataFrame, DataFrame]:`
*Site:* `pipelines/silver/build.py` :: `    "product_master",`
*Site:* `tests/pipelines/test_silver.py` :: `def test_the_category_survives_a_sale_the_cost_join_cannot_answer(`
*Disposition:* `pipelines/silver-reference-carries-the-product-dimension`, which is this branch —
**split out of `T011` deliberately**, on `#52`'s precedent: this is a defect in work that landed
the day before, found by the branch downstream of it, and *silver shipped missing the one
dimension every metric's grain requires* is a record a reader should find on a silver branch
rather than in commit four of a gold one. **Left open rather than closed by its own author**
*Status:* open

---
**A knob accepted in the wrong block, ignored without a warning, on a green run** · found
2026-09-04 · by `T011` checking what dbt had built rather than that it had built

`pipelines/gold/` runs dbt against local Delta. The first version put `file_format: delta` in
`profiles.yml`, under `outputs.local`, beside `type`, `method`, `schema` and `host`. **`dbt run`
reported `PASS=5 ERROR=0`.** Every table it built was **parquet**.

`file_format` is a dbt **model** config. In a connection block it is accepted, dropped, and
nothing is printed. Measured three ways on the same session, dbt-core 1.12.3 / dbt-spark 1.11.0 /
delta-spark 4.4.0 / Spark 4.2.0:

    file_format under `outputs` in profiles.yml   Provider = parquet
      select ... version as of 0                  -> [UNSUPPORTED_FEATURE.TIME_TRAVEL]
    the identical statement issued directly       Provider = delta      time travel works
    `+file_format: delta` under `models:`         Provider = delta      time travel works

**This is `CLAUDE.md`'s `grep -P` at one remove.** There, a missing option made *no matches* and
*no such option* the same two characters on a terminal. Here, a misplaced key makes *the format
you asked for* and *the default* the same green run — and it is worse in one respect: `grep`
exited 1. dbt exited **0**, and printed five green `OK created` lines naming five models that
were the wrong thing.

**And it was found by the session that had spent the day filing this exact family.** The first
report of this branch said the generated models *"execute unmodified against local Delta"*. The
SQL half was true; the Delta half was read off a knob that was never connected. It came out
because a reviewer's ruling made the storage property load-bearing — `delta.appendOnly` — and
checking that meant looking at what the tables actually were.

**The fix is not the interesting half.** `+file_format: delta` goes under `models:` in
`dbt_project.yml`, where it also reaches the compiled metric models without touching their
`{{ config() }}` — which is what keeps `make contracts`' byte comparison intact. The interesting
half is that `tests/pipelines/test_gold.py` now asserts the **provider of every built table**
rather than the config that was supposed to set it: *what came out*, never *what was asked for*.

*Site:* `pipelines/gold/dbt/dbt_project.yml` :: `# **`+file_format: delta` is here and not in `profiles.yml`, and that is a defect this branch`
*Site:* `pipelines/gold/dbt/profiles.yml` :: `# **`file_format` is deliberately absent here.** It is a model config and belongs in`
*Site:* `tests/pipelines/test_gold.py` :: `        assert described["Provider"] == "delta", f"{name} is {described['Provider']}, not Delta"`
*Disposition:* `pipelines/gold`, which is this branch — the misplaced key and the assertion that
would have caught it land together. **Left open rather than closed by its own author**
*Status:* open

---

**A single version parameter, applied to three tables whose version counters are independent** ·
found 2026-09-04 · by `T011` executing a compiled readout for the first time

`generated/readout/*.sql` emitted `version as of :data_version` on **every** relation it reads,
and its own header described that as *"the Delta version every source is pinned to"*. **Delta
version counters are per table.** Each starts at 0 and advances on its own writes, so one integer
cannot index two of them.

Measured on a gold build, which is the only way this could have been found:

    gold.decision_economics     max version = 0
    gold.waste                  max version = 0
    gold.experiment_assignment  max version = 0  after create
                                            = 1  after the assignment is written

A readout pinned at the fact tables' version therefore read `gold.experiment_assignment` **at
version 0, which is the empty `CREATE`** — the join found no arms and the query returned zero
rows. `assert {}`.

**It is structural rather than a matter of ordering.** The assignment table is written **once,
before the period opens, and never again** — that is doctrine rule 7, not an implementation
detail — while the fact tables are rebuilt on every dbt run. The one relation the design
guarantees will not move was being asked to move in step with the ones that do.

**The comment was false in prose, in the file, about the file**, which is what settled the fix:
one parameter per relation makes it true, and dropping the pin from the assignment alone would
have required rewriting it to carry an exception — and a comment with an exception in it is how
the next reader learns the wrong general rule. The rejected alternative's justification, *the
digest protects the assignment anyway*, is the argument that would let somebody drop the pin from
a fact table next.

**A third option was considered and refused rather than left unconsidered:** pinning at the
minimum of the three maxima, which would have made the failing test pass and left the artefact
wrong — the test bent to the defect. A fourth, `timestamp as of` with one shared moment, was
refused for a reason rather than a preference: a timestamp is a **lookup** into history that can
resolve differently after a vacuum or a restore, while a version is an identity, and the pin
exists so that the same query returns the same number.

*Site:* `src/holdout/contracts/compilers/sql.py` :: `def version_parameter(relation: str) -> str:`
*Site:* `pipelines/gold/readout.py` :: `def pins(text: str) -> dict[str, str]:`
*Site:* `tests/pipelines/test_gold.py` :: `def test_every_compiled_readout_binds_in_both_directions(path: Path) -> None:`
*Disposition:* `pipelines/gold`, which is this branch — the third payout of `docs/DECISIONS.md`'s
*"if gold does not match, the contracts move"* in one day, and the one that could not have been
found by any amount of reading. **Left open rather than closed by its own author**
*Status:* open

---

**The layout block's third crossing, and `make figures` is silent for the third time** ·
found 2026-09-04 · by `T011`, before creating the directory

`CLAUDE.md`'s layout lists `pipelines/gold/` under *"Declared and not yet built — phase 2 and
later"*. This branch builds it, so that sentence becomes false the moment it merges — after
`pipelines/ingest/` on 2026-09-02 and `pipelines/silver/` on 2026-09-03.

**The layout crossing is the third directory and `make figures` will not go red for it**, and
that is the sentence rather than the complaint: it is the same silence three times, and the third
is the one that establishes it is a property of the gate rather than an accident of two branches. Two rules could have caught it and neither applies: `layout_fabrications` exempts the
declared-future block by design, and `layout_packages` enumerates **top-level** directories git
tracks plus packages under `src/holdout/` — `pipelines/gold` is neither, so it is not in the
population at all. The row reads `22 = 22` before and after.

That is a **third** direction of the same one-sided question, and the entry that predicted it —
*"Nothing checks that a directory declared not yet built is still unbuilt"* — is open with a
disposition of `none`, because the edit it would force is to `CLAUDE.md` and that is the author's.
This is recorded as its third instance rather than as a new finding.

*Site:* `CLAUDE.md` :: `pipelines/gold/        dbt`
*Disposition:* none — the same as the entry it instantiates. The `CLAUDE.md` edit is the author's
and is with him; this branch does not touch that file
*Status:* open

---
**Three consumers named in three files, four emitted, and one of the three is not a view** ·
found 2026-09-04 · by `T011` counting what it had to build

`CLAUDE.md`'s claim 5 row, `PLAN.md`'s phase-2 heading and `T011`'s `closes` all say the metric
contract compiles into **three** things: *"a Delta view, the agent tool definition and the
readout query"*. `src/holdout/contracts/compilers/__init__.py` emits **four** per metric — a dbt
model, a **SQL table function**, an agent tool definition and a readout query — and `CLAUDE.md`'s
own `contracts/metrics/` section says four in as many words.

So `CLAUDE.md` says three in one place and four in another, and the two documents downstream of
it inherited the three.

**And the first of the three is not a view.** The dbt compiler emits `materialized='table'`;
`generated/dbt/models/metrics/*.sql` says so on its third line. *Delta view* would be a Unity
Catalog metric view, which the contract layer's rule 5 names as a **fourth** consumer added on
the estate — so the phrase in claim 5's row names the thing that is deliberately not there yet.

**Low stakes and filed anyway, because it is the family that has bitten three times this week:**
a count in prose that does not match the thing it counts. It matters slightly more here than
elsewhere because the SQL table function is the one consumer `T011` could **not** execute — it is
`create or replace function ${catalog}.metrics…`, a catalog object with a template variable — and
a count that omits it also omits the one gap.

*Site:* `CLAUDE.md` :: `compiled into a Delta view, the agent's tool definition and the experiment readout`
*Site:* `PLAN.md` :: `dbt. The metric contract compiles into a Delta view, the agent tool`
*Site:* `TASKS.md` :: `closes        The metric contract compiles into a Delta view, the agent tool definition and the`
*Disposition:* none — the `CLAUDE.md` half is the author's and the other two inherited it from
there, so correcting them alone would leave the three documents disagreeing in a new direction.
Filed with the three sites named so whoever opens that file has them together
*Status:* open

---
**The run is at its concurrency ceiling and the cheap lever is spent** ·
found 2026-09-04 · by `make check` refusing `T011` at twenty-one jobs

`tests/ops/test_ci_sharding.py::test_the_run_stays_under_the_concurrency_ceiling` computes
`3 + entries + combines + 1` by running `discover` rather than by writing a number down, and it
**refused** when `gold` became the twenty-first job against this account's documented ceiling of
twenty. Its own docstring had predicted the moment: *"the whole reason to compute it here rather
than to write it down is that the next entry will move it again."*

**It did not stop a bad change. It made a real cost visible at the moment somebody was about to
pay it without noticing**, which is what a gate is for and is rarer than catching a defect.

**The slot was bought by taking a shard off claim 2**, 8 to 7, which is acceptable and is not an
improvement: the measurement establishes only that the wall clock does not move, because
`claim-2-tests` at 446s is the matrix's longest leg and seven shards land ~144s under it. The
`Makefile` carries the figures and says in those words that the constraint chose the number.

**The forward count is the finding, and it is not a proposal.** Phase 2 has `T012`
(`evals/definition/`, which brings `make claim-5` and `make preview-audit`), `T013` (the two
dashboards) and `T014` (`pipelines/ml`) still open, and each may want an entry. **There are no
more shards to give at this price.** The levers left are:

    raise the ceiling                     an account setting — the author's, not a session's
    merge `silver` and `gold`             undoes `#50`'s separation and pays both extras
                                          (713 MB and 196 MiB) on one job whichever it runs
    put an engine's tests in `gate`       exactly what `T010` kept silver out of, on the job
                                          that runs on every push

The second and third are refused above rather than left unconsidered.

**The first was taken to the author on 2026-09-04 and declined, on grounds worth recording because
they are not about the shard count.** The ceiling is **not a correctness limit** — beyond twenty,
jobs queue, so it costs wall clock and not truth. Raising it is a **recurring subscription**, paid
from a budget earmarked for AWS, to solve a design question; seven is measured, free and
reversible, and its cost is one published figure becoming history. He kept seven.

**And shaving a shard buys exactly one task.** `T012` is a claim target and will want a job;
`T014` probably will. **There is no second cheap shard** — the sharding still earns the slots it
has, measured: 1,896s of draws against a 264s slowest leg.

**The structural question underneath belongs to `T016` and is deliberately not answered here.**
Three tasks each want an engine job and all three want the **same** installation: silver has one,
gold took a second, `pipelines/ml` will ask for a third — three slots for one dependency set. One
job for every engine test would cost one slot instead of three. **That is a question about the
whole**, which is what the phase-2 integration session exists for and exactly the kind of thing
answered badly one branch at a time; and when it is answered it is to be answered by **measuring**
what a combined job costs, not by projecting it.

*Site:* `tests/ops/test_ci_sharding.py` :: `def test_the_run_stays_under_the_concurrency_ceiling() -> None:`
*Site:* `Makefile` :: `CLAIM_2_SHARDS := 7`
*Disposition:* none — the question is whether the documented ceiling of twenty can be raised and
at what cost, which is an account fact and the author's to answer. Filed with the forward count so
that the next task to want a job finds the arithmetic rather than rediscovering it at the gate
*Status:* open

---

**A dependency introduced in this branch wrote a per-machine UUID into a tracked package** ·
found 2026-09-04 · by reading `git status` before committing rather than after

The first `dbt run` left two untracked things inside `pipelines/gold/dbt/`:

    .user.yml   id: <a UUID>      an anonymous machine identifier
    logs/       dbt.log

`send_anonymous_usage_stats` is **on by default**; dbt writes that id beside the profile and
posts usage events with it. `logs/` and `target/` also default to **inside the project**, which
here is a tracked package — a build writing into the tree it is built from, which is the same
shape `pipelines/gold/session.py` already refuses for Spark's `spark-warehouse/` and
`metastore_db/`.

**This repository is public and every commit is a publication at the moment it is made.** A
per-machine identifier is not a credential, but it is in the family the rule exists for, and it
arrived from a dependency rather than from anything anybody wrote.

**Three layers, in the order that matters.** `flags: send_anonymous_usage_stats: false` in
`dbt_project.yml`, so the file is not created at all — measured: with it false, no `.user.yml` is
written. `--log-path` and `--target-path` passed by `pipelines/gold/models.py`, so both output
directories are caller-chosen. And `.gitignore` entries as a **second** line of defence rather
than the first, because relying on one flag to keep a UUID out of a public repository is relying
on a flag.

**What has no layer at all is the general case, and the gates that could have seen it were each
looking for something else.** `make figures`' layout rows enumerate directories the map
**declares** — an untracked one a tool created is in neither the map nor the population. The
`secrets` job looks for credentials, and a machine UUID is not one. `make language` reads
repository content, and this was not content yet. **Three gates ran and none of them was pointed
at this**, which is a stronger statement than *nothing checks*: something would have had to be
built for it, and nothing was.

Two instances now, and **both were caught by a person reading `git status`** — this one, and
Spark's `spark-warehouse/`, `metastore_db/` and `derby.log` landing in the working directory,
which is recorded in `pipelines/gold/session.py`'s docstring and was found the same way, by
noticing an untracked directory appear in a worktree.

*Site:* `pipelines/gold/dbt/dbt_project.yml` :: `  send_anonymous_usage_stats: false`
*Site:* `pipelines/gold/models.py` :: `            "--log-path",`
*Site:* `.gitignore` :: `pipelines/gold/dbt/.user.yml`
*Disposition:* `pipelines/gold`, which is this branch, for the three layers above. **What stays
open is the general case**: no gate enumerates what a dependency writes into the tree, and both
instances so far were caught by a person reading `git status`. **Left open rather than closed by
its own author**
*Status:* open

---
**Three lists name the packages this tree may not have, and only one of them said so** ·
found 2026-09-04 · by `gate` going red on `#54` after a green local `make check`

`make typecheck` failed on CI with:

    pipelines/gold/models.py:69: error: Cannot find implementation or library stub
                                        for module named "dbt.cli.main"  [import-not-found]

**Not a collection failure and not the runtime guard's shape.** `lint` passed, the engine imports
are inside the functions that need them, and `make test` deselects `-m gold` cleanly. **mypy
resolves imports statically**, so it is a different consumer of the same absence: it fails on code
nothing runs, and it needs either the package or an entry in `[[tool.mypy.overrides]]`. `dbt` had
none.

**Three hand-kept lists name this set, and `T011` had to edit all three:**

    pyproject.toml        [project.optional-dependencies]      spark = […]  dbt = […]
    tests/boundary/…      ENGINES = ("pyspark", "delta", "deltalake")
    pyproject.toml        [[tool.mypy.overrides]] module = […, "pyspark.*", "delta.*"]

**Only the third said anything, and it said it on a runner.** The other two are silent by
construction: an override list that is short resolves fewer modules on a machine that has them
all, and a short `ENGINES` polices fewer names. `dbt` was missing from **both** the second and the
third — so today the guard would have refused neither an `importorskip("dbt")` nor a module-scope
`import dbt`, the two spellings it exists to refuse. Nothing had used either, so nothing was
broken; **the guard was simply blind, which is the state that looks most like coverage.**

**The second and third are now compared**, by `test_every_engine_is_ignorable_by_mypy` — the
direction that needs no package-to-module mapping. **It fired on its first run against a gap that
predates this branch**: `deltalake` had been in `ENGINES` since `T010` and was never in the
overrides. Nothing imports it, so mypy never had to resolve it and nothing went red. **The drift
was already two names wide before `dbt` made it three.**

**Nothing links the first list to the second, and that is where both drifts came from.** The
reason is in `ENGINES`' own comment — *"`delta` is `delta-spark`'s import name, which is not its
package name"* — and `dbt` makes the point twice over, since `dbt-core` and `dbt-spark` both
import as `dbt`.

**Measured rather than assumed to be impossible.** `importlib.metadata.packages_distributions()`
does invert it: `delta <- ['delta_spark']`, `dbt <- ['dbt-core', 'dbt-adapters', 'dbt-spark']`. So
the mapping exists. **A derivation over it still does not**, for three reasons that are all naming
and one that is not:

    deltalake  ->  None          an engine listed defensively and installed nowhere is invisible
    delta-spark vs delta_spark   distribution names normalise (PEP 503) and the two lists do not
    dbt extra declares holdout[spark]   a self-referential extra hides its own contents
    and it can only answer where the packages exist, which is not `gate`

So the gap is named and left open rather than closed badly: **the answer is available in the job
that has the packages and useless in the job that needs it.**

**And the generalisation is the line worth keeping.** Every local green on this branch was taken
with both extras installed, which is the one environment where this error cannot occur: **the
machine that builds the thing is the machine least able to see what its absence does.**

**What was already stated and not done.** After the previous runner failure this session said
`uv sync --locked && make check` was a thing it would run before pushing. It did not. **A stated
procedure that is not run is the same shape as a guard that is not armed**, and the answer is not
resolve — it is `make check-locked`, one command with a name, which is not a gate and does not
pretend to be one. What it changes is that *did you run `make check-locked`* has an answer and
*did you remember the two-step thing* does not.

*Site:* `pyproject.toml` :: `module = ["jsonschema.*", "pyarrow.*", "pyspark.*", "delta.*", "deltalake.*", "dbt.*"]`
*Site:* `tests/boundary/test_the_engine_is_never_skipped.py` :: `def test_every_engine_is_ignorable_by_mypy() -> None:`
*Site:* `Makefile` :: `check-locked:  ## make check in the environment CI's`
*Disposition:* `pipelines/gold`, which is this branch, for the two lists that can be compared and
for the named target. **What stays open is the first linkage** — extras to `ENGINES` — which is
measured above as available only where the packages are installed, and that is not the job it
would protect. **Left open rather than closed by its own author**
*Status:* open

---
**The largest number in the run is 731s of sequential mutations, and nothing recorded it** ·
found 2026-09-04 · by `T00M` decomposing a job it was about to tune around

The critical path is `max_leg + combine`, and `combine` is **99.6% mutations**. From the job's own
log timestamps:

    evals.uplift --combine          2.7s
    evals.gate_proof --claim 2    731s     8 mutations, sequential, slowest 88s of a 900s budget

So the run's chain is **288s of shards and 731s of `gate_proof`**, and **the shard count — the
number two tasks in a row proposed tuning — is a dial on 28% of it.**

Nothing in the tree records this. `make gate-proof` publishes the slowest **mutation** and its
budget, which is the right figure for *is a mutation looping*; there is no figure anywhere for
*what does the mutation pass cost the run*, and it is the largest single number in CI.

It is not a defect and nothing here is broken. `T00L` already moved the worst mutation from 806s
to 58s; what it did not do is make the pass concurrent, and `docs/DECISIONS.md` now records why
concurrency will not help — the eval already runs a pool sized to the runner's cores, so the work
is parallel one level down and four mutations at once divide the same four cores.

**What that leaves is a number with no owner.** `T00M` packed the ten idle entries because that
was free; the 731s is not free and was not touched, deliberately, because reducing it means
changing what the mutations do rather than where they run. **Recorded so the next session that
proposes tuning CI finds the decomposition rather than re-deriving it from the shard count.**

*Site:* `docs/DECISIONS.md` :: `**Claim 2's mutations run one at a time, and concurrency will not help** · deferred 2026-09-04`
*Site:* `ops/ci_pack.py` :: `def pack(targets: list[str], makefile: str) -> list[list[str]]:`
*Disposition:* none — this is a measurement rather than a defect, and the thing it would take to
act on it is a change to the mutation pass that no task has asked for. Filed with the
decomposition so the number is not rediscovered from the outside a third time
*Status:* open

---
**The contract's `rounding` block is inert on this corpus, and v3's justification with it** ·
found 2026-09-04 · by `T012` planting two mutations that survived

`contracts/metrics/*.yaml` declares `rounding: {mode: half_even, decimals: 2}`, and
**metric v3 exists because of it.** Its own restatement:

> v2 rounded half_up. Two consumers of the same definition can then disagree by one cent — the
> dbt path through SQL round() against the Python reference implementation, whose Decimal
> default is half_even — and claim 5 compares as integers with no tolerance, so a one-cent
> disagreement is a failed claim for a stupid reason.

**On this corpus that disagreement cannot arise.** Gold builds `price_paid` and
`unit_cost_as_of` as `cents / 100` and `qty` is an integer, so every cell is an **exact number
of cents**:

    qty 3 · price 1.26 · cost 1.00  ->  0.78, exponent -2
    rounding it to 2dp changes it:  False

`bround(x, 2)` on a value already exact in cents is the **identity function**, and `half_even`
and `half_up` differ only on an exact half at the third decimal that this data never has. **So
the block is inert across every consumer** — the dbt model, the SQL function, the readout and
both Python paths — and v3's justification is **unverifiable on this data.**

**And it is a controlled comparison rather than an argument, which is the form worth reading.**
One mutation, correctly built, unchanged: it **rounds each row before summing.**

    over 480 corpus cells        SURVIVED   nothing to round; bround(x, 2) is the identity
    over the same run plus one
    constructed cell at 0.1250   BIT        the exact sum rounds to 0.12, the early-rounded
                                            rows to 0.13

**The only thing that changed is the data.** A reader can check that without following any
arithmetic about exponents: `half_even` and `half_up` cannot part company on this corpus, and
here is the cell where they do.

**The same comparison sharpens v3's problem rather than softening it.** The distinction v3 exists
for is now demonstrably **real** — the cell proves it — and demonstrably **unreachable from the
corpus**. Both halves measured rather than one asserted.

A second plant survived beside the first for an unrelated reason recorded below, and reporting
the two as one story was a mistake corrected before it reached the author.

**What `T012` did about it, and what it did not.** `evals/definition/build.py` constructs **one
cell** at `0.1250`, where `half_even` gives `0.12` and `half_up` gives `0.13`, appended to
`gold.decision_economics` so all three mechanisms read it. That is claim 4's practice, not a new
one — `evals/censoring/`'s `C2` asks its question *"over every censored store-day the corpus
produced and every one the sweep constructed"*, and `CLAUDE.md` endorses it by name.

**A constructed cell proves three mechanisms round alike on a value the corpus never produces.
It does not prove the corpus should produce one**, and it does not make the block live for
anything else that reads it. **A reader who sees `make claim-5` green should not conclude the
rounding question is settled.**

**The eventual answer is a corpus with sub-cent content** — real grocery has it wherever cost is
per kilogram — which would make the block load-bearing everywhere rather than in one constructed
cell. That is deliberately not this branch: it changes the data under claims 1 through 4 and must
not ride in on claim 5.

*Site:* `contracts/metrics/category_margin_per_store_week.v3.yaml` :: `    half_even is now the contract and every consumer is compiled to it.`
*Site:* `evals/definition/build.py` :: `CONSTRUCTED_CELL = ("ST-CONSTRUCTED", "2026-W01", "constructed")`
*Disposition:* none — the constructed cell closes the *mechanism* question and this is the
*corpus* question, which is a task nobody has opened. Filed against the contract and the corpus
rather than against `evals/definition/`: claim 5 is where it was found, not what it is about
*Status:* open

---
**`TASKS.md` asserts what a `DECISIONS.md` entry says, and the entry says otherwise** ·
found 2026-09-04 · by `T012` reading the cited entry rather than the citing sentence

`TASKS.md`'s `T012` block: *"`make preview-audit` … **This is where `preview-audit` first has
something to act on; `DECISIONS.md` defers it to exactly here.**"*

`docs/DECISIONS.md`'s entry: *"Unlock condition: **the first Terraform layer, and** the first
time a preview surface is considered."*

**`T012` is `evals/definition/`. It is not a Terraform layer, and there is still no `infra/`.**
So the deferral does not unlock here and the sentence claiming it does is false about the file
it cites.

**And the surface that fired the other half is gone from the design.** `T015` fired *a preview
surface has been considered* on the **PostgreSQL connector for Lakeflow Connect**; route 2 then
removed the connector, the gateway and the RDS, and `T019` closed *not built*. This register
already carries the distinction, from the `gone` finding: **route 2 removes a surface, not the
condition.**

**So the inventory is not empty — it is undetermined**, and those are different. The connector is
removed; **Zerobus is unresolved in one direction** (`docs/DAY-ONE.md` records an overview page
carrying no preview banner and one unconfirmed contrary search result); the Unity Catalog metric
view is out of scope by `T012`'s own block and lives on the estate. **A gate over an undetermined
population is worse than one over an empty population**: it would report *no claim's proof path
touches a preview surface* while nobody knows what the surfaces are.

**Both facts are true and both keep the deferral open**: the condition is unmet **and** the
inventory is unknown.

**This is the second instance, and how both were found is the transferable part.** `F2` on `T011`
was the same shape — `TASKS.md` deferring the generated SQL's execution to phase 3 while the
entry it cited unlocked at phase 2 — and **both were found by opening the cited entry rather than
by reading the citing sentence.** Instances recorded, no rule: two is not a shape, and the
correction each time is that a deferral naming its own unlock outranks a parenthetical about it.

**A third was proposed on 2026-09-04 and refused, and the ground is recorded because the next
reader will make the same surface match.** The candidate was `docs/DECISIONS.md`'s claim-2-README
deferral naming `T012` as its unlock. It shares the shape — *a sentence about another document
that turned out wrong* — and not the mechanism. `F2` and the entry above describe an **existing
text** incorrectly and are **detectable by reading**, which is how both were found; the countermeasure
is a habit, open the cited entry. That one **cites nothing**: it predicts what a task not yet
written would touch, and it failed because the task chose differently, which no reading of any file
could have caught in advance. Its countermeasure is a different rule and already exists — *a
condition names an event, not a session*, and not a task. **Two failure modes, two countermeasures,
and a rule generalised from a miscounted three is scoped to whatever the three happened to wear.**
This register's own history is the argument: the *guard tested by its author* row took nine
instances, and every early version was scoped to the form the known cases wore.

*Site:* `TASKS.md` :: `              any claim's proof path touches one. This is where preview-audit first has something`
*Site:* `docs/DECISIONS.md` :: `*Unlock condition:* the first Terraform layer, and the first time a preview surface is considered.`
*Disposition:* none — the correction is a restatement in `TASKS.md`, which `T012` makes, and the
deferral stays open on its unmet half. What has no owner is the inventory being undetermined,
which is `T015`'s Zerobus question and is the author's to settle
*Status:* open

---
**A packed job's ceiling check abstains for every target with no world cache** ·
found 2026-09-04 · by `T012` reading the check it was about to be measured by

`ci.yml`'s packed job compares its own elapsed time to `CI_ENTRY_CEILING`, and abstains first:

    if [ "${{ steps.worlds-cache.outputs.cache-hit }}" != "true" ]; then
      echo "cold: the world cache missed, so this entry regenerated what a warm one restores."
      exit 0
    fi

**The escape is correct for what it was written against and reads one thing while meaning
another.** `cache-hit != true` is being used as a proxy for *this entry regenerated its worlds*.
The two coincide for every target that existed when it was written, because all of them either
use `evals/uplift/cache.py` or are fast enough never to matter.

**`.worlds` is written by `evals/uplift/cache.py` and by nothing else** — measured, one file in
the tree names that directory. `claim-5` builds its world through `corpus.world.prepare` directly
and writes no cache entry, so its key is never populated, `cache-hit` is `false` on **every** run,
and the ceiling is never applied to it. Not on the first run — permanently.

**This is the disarm the check's own comment predicted, arriving one target later in a shape the
comment did not name.** It says: *"it is a check that can be silently disarmed by a cache that
stops working, and nothing here detects that. A run where every entry reports cold is the visible
symptom."* The symptom named is a cache that **breaks**. What actually happened is a target that
never had one, and it produces a single permanently-cold entry among warm ones — which reads as
normal rather than as a symptom.

**The condition that would be right is available in the job and is not a target list.** After the
run, an entry that regenerated worlds has a non-empty `.worlds` and an entry that never uses them
does not, so *abstain only when the cache missed and this entry actually built worlds* separates
the three cases with no hard-coded names. **It is deliberately not changed here.** It is `T00M`'s
mechanism, `claim-5` has never run on a four-core runner, and enabling the ceiling for it on the
strength of a laptop measurement is the defect `CLAUDE.md` names about numbers in configuration —
in the very check whose job is to catch it. **The first CI run is the measurement**, and whoever
declares `CLAIM_5_COST` from it is the one who can also close this.

> **Measured 2026-09-04, run 33848508391, and the falsifier was named before it ran.** This entry
> predicts that `claim-5` prints `cold` and is never judged; the thing that would refute it is the
> bin printing `warm`, which was said in advance rather than after. It printed:
>
>     this entry took 674s against a ceiling of 1032s
>     cold: the world cache missed, so this entry regenerated what a warm one restores
>
> **674s against a 1,032s ceiling, and the ceiling was not applied.** The entry is comfortably
> inside it, so nothing was hidden this time — which is exactly why the defect is worth keeping
> open. **A check that would have passed anyway did not run**, and nothing on the run distinguishes
> that from a check that ran and passed. `CLAIM_5_COST` is now declared at 750, so a future change
> that made this target slower would be a stale cost — and the mechanism that turns a stale cost
> into a red run naming the bin is the one that abstains here, permanently.

*Site:* `.github/workflows/ci.yml` :: `          if [ "${{ steps.worlds-cache.outputs.cache-hit }}" != "true" ]; then`
*Site:* `evals/uplift/cache.py` :: `CACHE_DIR = Path(os.environ.get("HOLDOUT_WORLD_CACHE", REPO_ROOT / ".worlds"))`
*Disposition:* the next task that declares `CLAIM_5_COST`, which needs the same run this needs
*Status:* open

---
**A seal test searched a wall clock for a three-digit needle, and went red 1 run in 241** ·
found 2026-09-04 · by `T012` running the suite, not by reading it

`tests/corpus/test_world_seal.py::test_the_truth_is_not_lying_in_the_file_in_plain_sight` reads
the whole sealed file as text and asserts that five strings **taken from the truth itself** do not
appear in it. The docstring's argument is right and is the reason the test is good: *a hand-written
list would test the author's imagination; this tests the file.*

**One of the five needles is a bare integer, and one part of the haystack is a clock.** The nonce
is derived rather than random — `corpus/world/seal.py` says so, deliberately, so that a rebuilt
world produces a byte-identical seal — so **`sealed_at` is the only byte that changes between
runs**. At `W3`, `smoke`, seed `seal`, `totals["acks_failed"]` is **248**, and a three-digit needle
inside `2026-09-04T07:55:39.540625+00:00` collides in **0.414% of runs — about 1 in 241**, measured
over 500,000 sampled timestamps.

**A clock reading `…:24:8…` is not the truth leaking.** The collision answers a question nobody
asked, and it can only ever produce a false red: the assertion is a `not in`, so chance moves it in
one direction. Every job that runs the suite carries the 1-in-241, which is why it showed up as a
single unreproducible failure inside a full run and passed on every attempt to reproduce it.

**Fixed by narrowing the haystack rather than the needles.** The search now runs over the seal with
`sealed_at` removed — the deterministic part, which is the only part that could carry a leak. The
needles are unchanged and still come from the truth. **Checked by planting**: a needle written into
the seal's `note` is still seen, so the narrowing removed a chance collision and not the guard.

**How it was found is the part worth keeping.** It appeared in a `make check` run for an unrelated
change and passed on the next four; the temptation is to call it a flake and move on. It is a flake
— *with a mechanism*, a probability, and a one-line fix, and every one of those came from measuring
the needle against the haystack instead of re-running until it went green. **Pre-existing; nothing
in `T012` touches this file or the seal.**

*Site:* `tests/corpus/test_world_seal.py` :: `def test_the_truth_is_not_lying_in_the_file_in_plain_sight(sealed: Path, readout: Path) -> None:`
*Site:* `corpus/world/seal.py` :: `        "sealed_at": datetime.now(UTC).isoformat(),`
*Disposition:* fixed in the test on 2026-09-04. What is **not** closed is the general shape — a
needle that is a bare number searched in text containing a timestamp — and nothing enumerates the
other places it could occur
*Status:* open

---
**A packing claim was verified against a target list typed by hand** ·
found 2026-09-04 · by `T012` reading the job name on the run after

The commit declaring `CLAIM_5_COST := 750` asserted, in the `Makefile` and in `TASKS.md`, that it
**changed no packing decision** and that `claim-5` was *"its own bin at 674, at 750 and at the
default alike"*. Both are false. Measured over the population `discover` actually enumerates:

    undeclared   800 [claim-5]              742 [claim-1, gate-proof]
    at 750       780 [claim-5, gate-proof]  712 [claim-1]

The declaration moved `gate-proof` (30s) out of `claim-1`'s bin into `claim-5`'s. Five bins either
way, so no slot moved — but **two bins changed contents, so two cache namespaces changed**, and the
next run's job is named `claim-5 gate-proof`. That name is how it was found.

**The claim was not unchecked. It was checked against the wrong population.** The verification ran
`ci_pack.pack` over a list of targets typed into a one-off script, and that list omitted
`gate-proof`. `discover` reads its population out of the Makefile with
`^(claim-[0-9]+|gate-proof|preview-audit|silver|gold):`, and asking it would have cost the same
keystrokes as typing eight names.

**This is this repository's coverage rule applied one layer in.** *A gate reports on what it
examined; it becomes a lie when it reports what it examined as if it were what exists.* Every
instance recorded so far is a **gate** enumerating its own population — `ruff`'s file list, `ci`'s
`claim-[1-7]`, the `layout` row. This one is a **verification** doing it: not a check that ships,
but the act of confirming a sentence before committing it. It has no gate behind it and never will,
which is the same place the *guard tested by its author* defects live.

**And the shape is the sharpest available**, because it happened inside a commit whose entire
subject was setting a number from a measurement rather than a projection, written by a session that
had spent the day restating other people's unmeasured figures. **The care was real and it was
pointed at the number. Nothing was pointed at the population the number was checked over.**

**Second observation, incidentally: the bin took 653s** — `claim-5` plus a 30s target, in less wall
clock than `claim-5` alone took at 674s. Two points, 674 and 653, about 7% apart across consecutive
runs of unchanged work, which is the first direct evidence for the variance argument the
declaration rests on and does not change it.

*Site:* `Makefile` :: `CLAIM_5_COST := 750`
*Site:* `.github/workflows/ci.yml` :: `          targets="$(grep -oE '^(claim-[0-9]+|gate-proof|preview-audit|silver|gold):' Makefile \`
*Disposition:* the sentences are restated in place per doctrine rule 4 and the delta is recorded.
What has no owner is whether a verification of a packing claim should be a target rather than a
script somebody types — `ops/ci_pack.py` could expose the population `discover` reads, and nothing
today makes using it easier than not
*Status:* open

---
**Two properties the design requires and the corpus cannot express — record them as a pair** ·
found 2026-09-04 · by `T012` and `T014`, one each, neither knowing about the other

**Sub-cent cost content.** Gold builds `price_paid` and `unit_cost_as_of` as `cents / 100` and
`qty` is an integer, so every metric cell is an exact number of cents. `bround(x, 2)` is the
identity and `half_even` and `half_up` never part company, which makes the `rounding` block of
every metric contract inert — measured by planting, and `evals/definition/` constructs one cell to
exercise what the corpus cannot reach.

**Price variation independent of the arm.** `corpus/world/policy.py`'s `price_cents(base, hours)`
is a step function with no noise and no exploration, so price is a deterministic function of
hours-to-expiry within an arm. Measured at `rehearsal` over `PriceDecision` events: **W1 has one
discount level per hours-bucket, W6 has two, and within `(hours, arm)` there is exactly one.** So
demand at a price the policy never set is unidentified on ordinary history and, in a world with an
experiment running, identified only from the treatment contrast the readout exists to measure.
`CLAUDE.md` names the remedy — *deliberate price randomisation on a small share of decisions* —
and it is not built. `pipelines/ml/` is the first consumer that needed it and does not fill the
hole: the model forecasts units at the price the policy sets, and says so.

**They are recorded together because whoever fixes either one should find both.** Each changes the
data of every world; each invalidates claim 2's world caches; each costs a cold CI on every touched
module. `T00M`'s lesson applies exactly — **two changes to the same expensive thing, batched, cost
once** — and nothing else in this register would have put them side by side, because they were
found six hours apart by two tasks looking at different layers.

**Neither is a defect in the corpus.** `corpus/world/` was built before either consumer existed and
is correct about what it set out to generate. What is recorded is that two downstream claims have
now each met a limit of it, and that the limits are cheaper to lift together than apart.

**What happens at decision time, asked because the finding stopped at the model and the sentence
differs completely either way.** `core.pricing.Scenario` takes `expected_units` per candidate
price, so the decision path asks for something no model fitted on this corpus can supply. **The
ladder covers it, the state is coherent, and doctrine rules 1 and 2 both hold**: rule 1 declares
the deterministic markdown ladder the safe state of the fresh path *"when the freshness gate fails,
when the model is unavailable, or when any input is stale"*, `tests/core/test_composition.py`
proves a ladder price certifies at every rung, and a ladder price carries `FALLBACK_LADDER` to the
label, the P&L and the monitor. **So this is not *the decision path has an input nothing can
supply*.** Something supplies it, the design anticipated exactly this, and the fallback is visible.

**The consequence is worth naming rather than leaving as reassurance: on this corpus the model
path is unreachable, so every fresh markdown decision falls to the ladder and the decision monitor
would read 100% fallback.** That is the system honestly reporting it has no usable model — which
is what rule 2 exists to make visible — and it is a different sentence from *the system working*.

**Does the estate inherit it? Yes, and it was checked rather than assumed.** Phase 3's `backfill`
trains on eight months of history from this same generator, so the question is whether anything
about scale introduces price variation. Measured over `PriceDecision` events at every declared
scale, discount levels within one `(hours_to_expiry, arm)` cell:

    smoke      W1  1,320 decisions    1 level     W6  1,380     1 level
    rehearsal  W1  17,640 decisions   1-2 levels  W6  17,820    1-2 levels
    harness    W1  295,764 decisions  1 level     W6  295,816   1 level

**One level, at 320 stores as at four.** The `1-2` at `rehearsal` is not exploration and is worth
saying so: it is `price_cents` rounding a rung to the cent — `max(1, (kept + 50) // 100)` — so one
base price realises a 50% rung as 49% and another as 50%. That is variation **across SKUs at one
depth**, perfectly confounded with base price, not a second price for the same product.

**And it is structural, not a fact about size**: `price_cents(base, hours)` depends on the base
price and the hours only, and the depths come from the policy's rungs, which are the same in every
world and at every scale. `harness` is also the largest scale this repository declares —
`CLAUDE.md` restates that no declared scale reaches 1,200 — so it is the largest thing phase 3
could run.

> **So the phase-3 demonstration would show the ladder working and never exercise the model path.**
> A coherent, honest system doing exactly what doctrine rule 1 says, and **a materially different
> demonstration from the one this project describes.** That is a sentence the author needs before
> phase 3 opens rather than inside it, and it belongs beside the missing join below because the two
> together decide what the estate can show.

**And one thing genuinely does not exist, named here because it is the join between two halves that
do.** *Nothing anywhere converts a model into a scenario table.* `selection.py` says so about
itself — *"`Scenario.expected_units` arrives as data"* — and the only tables in the repository are
worked by hand in `tests/core/test_composition.py`. `T014` did not build one and it is not in its
scope: a producer needs the price response that is the first half of this finding. **So the gap is
not that the model is weak; it is that the adapter between the model and the decision path has no
owner**, and that belongs in front of `T016` in those words.

*Site:* `corpus/world/policy.py` :: `    def price_cents(self, base_price_cents: int, hours_to_expiry: float) -> tuple[int, int]:`
*Site:* `pipelines/ml/__init__.py` :: `What this package forecasts, and the measurement that decided it`
*Disposition:* the author's, and it is one decision rather than two — whether the corpus gains
sub-cent costs and price exploration in one change. Neither claim is blocked meanwhile: claim 5
constructs its cell and `pipelines/ml/` narrows what it forecasts
*Status:* open

---

**Two thresholds declared from reasoning, both convicted by the first measurement** ·
found 2026-09-04 · by `T014` running the pipeline it had just written

`contracts/ml/training.yaml` declared `rmse_ceiling_units: 6` and
`segment_calibration_tolerance_pct: 10`. Both were written with an argument beside them, both
arguments were sound, and both numbers were wrong the first time anything measured them.

    rmse_ceiling_units: 6        mean demand is 34 units per store-SKU-day; the honest model
                                scores 13.6, so the gate refused every model that could exist
    segment tolerance: 10%      the median segment's own standard error is 5.13%, so ten
                                percent is 1.9 sd — an expected 1.2 false alarms every run
                                over twenty-one segments

**The second is the worse one and it is the one that would have survived.** A gate that refuses
everything is noticed on the first run. A gate that refuses a good model **most** runs is noticed
as flakiness, and the reasonable response to flakiness is to widen the tolerance until it stops —
which is how a gate is disarmed by people acting sensibly, with a commit message that says
*reduce noise*.

**Both were fixed by making the threshold relative to something the data supplies**: RMSE as a
share of the do-nothing baseline, and per-segment calibration in multiples of that segment's own
standard error. Neither then needs to know the scale of the corpus, which is the property that
made both original numbers guesses.

**And a third, one order rarer, found by review rather than by measurement.** The fix above
replaced the flat 10% with **three standard errors** — and three standard errors applied to the
**worst of twenty-one segments** is not three standard errors. Measured: it refuses a
well-calibrated model on **5.52% of runs**, one in eighteen, which is precisely the rate the
paragraph above says a tolerance gets widened at. **And it degrades with the corpus**, which is the
half nobody would have noticed: 12.6% at 50 segments, 41.8% at 200, **93.3% at 1,000**.

> **A fixed multiple is a threshold whose meaning depends on a population size nothing
> enumerates** — this repository's coverage rule wearing a number instead of a verb.

So the contract now declares the **family-wise false alarm rate** and the per-segment limit is
derived from it and from how many segments were judged, by Bonferroni. At 21 judged segments the
limit is 3.04 standard errors; at 200 it is 3.66. **The declared number is the one that tells a
reader whether a red run is real**, and the limit is what is computed from it.

**Three instances now, each a level up from the last, and each found a different way.** The first
was caught by the gate refusing everything on the first run. The second by measuring the noise
floor. **The third by a reviewer asking whether the correction had been applied for testing
twenty-one segments** — a question no measurement I had taken would have raised, because every one
of them was of a single segment.

**What makes this a finding rather than two corrections.** `CLAUDE.md` already says an assertion
wearing a number is set from a measurement of the thing that will run — and this atom's author had
spent the same day applying that rule to `CLAIM_5_COST`, refusing to declare it before a runner
had executed the target. **The rule was in hand, recently used, and did not fire here**, because a
contract value with a paragraph of justification beside it does not look like an unmeasured
number. It looks like a decision.

> **Justification as camouflage.** Every other instance in this register is a fact that was
> **missing** or **unread**. This one was *decorated*: the number had a paragraph beside it
> explaining exactly why it was that number, and the paragraph is what stopped anybody asking what
> it had been checked against. The tell is not the absence of an argument. **It is the absence of a
> measurement the argument was checked against**, and an argument is what hides that.

*Site:* `contracts/ml/training.yaml` :: `  rmse_share_of_baseline:`
*Site:* `contracts/ml/training.yaml` :: `  segment_family_false_alarm_rate:`
*Disposition:* both restated in place with the prior wording kept, per doctrine rule 4. What has no
owner is whether other contract values carry the same shape — `inference.yaml`'s nine are the
obvious population and nothing has measured them against what they gate
*Status:* open

---

**A module's docstring claimed a separation the code did not have, found by a planted test** ·
found 2026-09-04 · by `T014`'s `P4` plant refusing to bite

`pipelines/ml/calibration.py` opens with *"This module measures and that module judges, so a
threshold cannot be quietly relaxed by the code that computes the quantity it is compared
against."* `promotion.py` says the same thing from the other side.

**It was false.** `measure` took `min_segment_days` and stamped a `judged` flag onto every
segment; `assess` then read `calibration.judged_segments` and compared its own contract value
against a decision another module had already made. The threshold was applied in the module whose
docstring says it applies none.

**It was found by a plant failing, not by reading either file.** `P4`'s test raises
`min_segment_days` above every segment's size and requires the gate to refuse — and nothing
happened, because the judging had been done one module earlier with a different value. Both
docstrings had been read several times that hour, by their own author, and each one describes the
architecture the author intended.

**`Calibration.judged` is now a method taking the threshold**, so the only numbers crossing into
that module are the ones being measured. The prose did not change; it became true.

*Site:* `pipelines/ml/calibration.py` :: `    def judged(self, min_segment_days: int) -> tuple[SegmentCalibration, ...]:`
*Disposition:* fixed. The class stays open — **prose describing a separation the code does not
have** is the same family as *prose that claims a check nobody wrote*, and nothing enumerates where
else a module says it decides nothing while taking a threshold as an argument
*Status:* open

---
**The single most important screenshot in the project has no data source** ·
found 2026-09-04 · by `T013` reading what its own `closes` sentence would need

`TASKS.md`'s `T013`: *"**The refused version of the readout screen is the single most important
screenshot in the project.**"* `CLAUDE.md` says the same thing and describes the screen: four
check tiles, then *"either the uplift with its confidence interval, or the refusal and its reason
code, at the same size"*.

**Nothing produces that row.** `gold.readout` does not exist — `pipelines/gold/` builds two of
family C's four tables and says why the other two are absent: *"exposure and outcomes are
collected by a running experiment, which is phase 3."* And the compiled readout query is not it
either: `generated/readout/*.sql` returns `arm · store_id · iso_week · category · metric_value`,
**computes no uplift and carries no reason code**. It is the input to an estimator, not the
estimator's answer.

**So the screen the design calls its most important artefact is the one screen whose data has no
producer.** Both halves either side of it exist — `holdout.core.experiment` closes a readout and
returns every field, and the dashboard resource is compiled and validated — and the join does not.

**This is the same kind as the model-to-scenario-table gap `T014` filed**, and they are named
together for the same reason: *halves that exist and a join that nobody owns*. A gap with no owner
is the one kind that survives every atom, because every atom can correctly say it is not theirs.

**What `T013` did instead of inventing a schema.** The dashboard names columns for the absent
table, and they are the fields of `holdout.core.experiment.readout.Readout` — the type the core
already returns and the one phase 3 will materialise — with
`tests/contracts/test_dashboard.py::test_the_readout_columns_are_the_core_types_own_fields`
comparing the two **in both directions**. So the screen consumes a declaration that exists rather
than one somebody wrote for it, and a field renamed in the core turns the build red. **That is not
a fix and is not offered as one**: it makes the naming honest, and the row still has nobody to
write it.

*Site:* `src/holdout/contracts/compilers/dashboard.py` :: `READOUT_COLUMNS: tuple[str, ...] = (`
*Site:* `pipelines/gold/__init__.py` :: ``C`    `experiment_assignment` · `exposure` · `outcomes` · `readout`        two of four`
*Disposition:* `T016`, alongside the model-to-scenario join. It is not `T013`'s — a producer needs
the experiment to have run — and it is not phase 3's to discover, because what the estate can
demonstrate is decided before it opens
*Status:* open

---

**`terraform validate` passes a dashboard whose SQL is broken over a table that does not exist** ·
found 2026-09-04 · by `T013` testing its own stopping condition before relying on it

`T013`'s `stop_at`: *"when the definitions consume the metric contract and `terraform validate`
passes."* Two halves. **Only the second is mechanised, and it cannot see the first.**

Measured against the real provider — `databricks/databricks` 1.130.0 — with a
`databricks_dashboard` whose `serialized_dashboard` contained

    select nonsense from table_that_does_not_exist where 1=

broken syntax, a column that does not exist, a table that does not exist:

    Success! The configuration is valid.

**`serialized_dashboard` is a string.** `validate` checks HCL and the provider's resource schema
and stops there. So the declared stopping condition is satisfied by a dashboard that re-expressed
the metric wrongly, against tables nobody built — **a declared stopping condition that does not
test the declared closing condition**, which is the third time this repository has recorded that
shape.

**Closed by making the consumption structural rather than by widening the assertion.** The readout
screen's dataset SQL **is** `compile_readout(metric)` — the same call `generated/readout/` is
written from, not a copy of it — the four check tiles are derived from `at_readout`'s own `check`
field, the monitor names all twelve `at_decision` codes, and both screens are artefacts under
`generated/` that `make contracts` byte-compares. A drifted query is a red build, not a red
screenshot six months later.

**What is worth keeping is the order.** The measurement came before the design: the plant was run
against the provider *before* the layer was written, so the compiler exists in the shape it does
because `validate` had already been shown blind. **A stopping condition trusted rather than tested
is a gate whose coverage nobody measured**, and this one covers none of what the atom is about.

*Site:* `infra/lakehouse/README.md` :: `    select nonsense from table_that_does_not_exist where 1=`
*Site:* `Makefile` :: `terraform:  ## terraform validate over every layer under infra/`
*Disposition:* closed in `T013` by the byte comparison. The **class** stays open: nothing
enumerates which other `stop_at` conditions in `TASKS.md` are satisfiable without testing what
they name
*Status:* open

---
**The explained-collision pair key degrades to the bare identifier** ·
found 2026-09-04 · by the reviewer, when a fifth same-name entry was about to be added

`evals/oversight/checks.py`'s `EXPLAINED` is keyed by a **pair** — the name here and the name
there — and its comment records why, as a finding of its own:

> *"**The key is a pair, and that was a finding.** It was the bare identifier until oversight
> level 2 pointed out what that excuses: an entry for `members` would have pre-approved **any**
> future `members` anywhere in the package — including one that really is a collection of people
> — and `O12` would have stayed green, because the name still matched something."*

**The entry is `("members", "members")`.**

**For a same-name collision the pair key *is* the bare identifier.** A future local `members`
colliding with the published `members` matches that key exactly, and is pre-approved — which is
the outcome the pair was adopted to prevent, in the very example the comment uses to explain it.

Measured over the eleven entries:

    same-name   4   agent · candidate · members · parents
    differing   7   AGENT vs agent · agent_tool vs agent · compile_agent_tool vs agent ·
                    candidate_weeks vs candidate · url vs URL · weight_c vs weight ·
                    weight_t vs weight

**So the pair genuinely protects seven and protects nothing on four**, and `height` — added the
same day — would have been a fifth. The mechanism is not wrong; it is **partial in a way its own
justification does not say**, and the sentence a reader takes away is that the case is covered.

**Found because a fifth same-name entry was about to be added**, and by the reviewer rather than
by the session adding it. Nothing measured it before: the four have been there since T006 and the
count had never been taken.

> **A mechanism whose recorded justification names the case it fails on is worse than one with no
> justification**, because the justification is what stops anybody checking.

**What would fix it is a design question rather than a longer key**, which is why this is filed
rather than fixed. An explanation would have to be keyed to something that distinguishes *this*
`members` from a future one — a module, a type, a line — and each of those has a cost the pair
does not: a key carrying a path goes stale on a move, and a key carrying a line goes stale on an
edit. **The pair was chosen because it is stable. What it buys in stability it gives back on every
same-name collision**, and that trade has never been stated.

*Site:* `evals/oversight/checks.py` :: `EXPLAINED: dict[tuple[str, str], str] = {`
*Disposition:* `T016`, with the other two joins. It is a design question about what an explanation
is keyed to, it blocks nothing, and the four entries it affects are each individually sound —
which is what makes it a shape rather than four defects
*Status:* open

---
**A coverage guard enumerated its population by the property it was about to check** ·
found 2026-09-04 · by the reviewer, on a target with one layer where it could not yet be wrong

`make terraform` was written to validate *"every layer under `infra/`, with the population
enumerated by a glob rather than by a list somebody keeps"*. It globbed `infra/*/`, then:

    [ -f "$layer/versions.tf" ] || continue

**A directory without a `versions.tf` was skipped with a bare `continue` and counted nowhere.**
`found` counted only the layers it validated, so the `found == 0` guard could not see a layer that
existed and was passed over. **The coverage rule at one directory's depth, inside the target
written to enforce it** — *a gate reports on what it examined; it becomes a lie when it reports
what it examined as if it were what exists.*

**The shape is sharper than a missing branch: the guard enumerated its population by the very
property it was checking for.** A layer counts as a layer *because* it has the file whose absence
is the defect, so the defect makes its own instance invisible. That is not the same as forgetting
a case — no amount of care inside the loop would have found it, because the loop never saw one.

**It could not be wrong with one layer, which is exactly when it was worth reading.** Phase 3 adds
four — `bootstrap`, `foundation`, `pipelines`, `ml`, `serving` — so it would have become wrong by
**construction** rather than by accident, and the first symptom would have been a green
`terraform` line on a run that validated one layer of five.

**Fixed here rather than filed alone**, because the fix is not a judgment call: the population is
every directory under `infra/`, a directory with `.tf` files and no `versions.tf` is **red rather
than skipped**, and a directory with no `.tf` at all is reported as examined-and-not-a-layer.
Both shapes are planted against by hand before and after.

**Who found it, because it is the transferable part.** Not the author of the target, who had
written the sentence about enumerating from the tree and believed it. A reviewer, on the grounds
that *there is one layer today so it cannot yet be wrong — which is exactly when it is worth
reading.* **The window in which a coverage guard is unfalsifiable is the window in which it is
cheapest to check.**

*Site:* `Makefile` :: `terraform:  ## terraform validate over every layer under infra/`
*Disposition:* fixed 2026-09-04, with the prior wording kept per doctrine rule 4. The **class**
stays open: nothing enumerates which other gates in this repository decide their population by a
property they are also checking
*Status:* open

---

**An extension of a principle was written up as a precedent the list already carried** ·
found 2026-09-04 · by the reviewer, in the entry written the hour before

`evals/oversight/checks.py`'s new `("height", "height")` explanation said the two alternatives
were *"refused for reasons this list already carries"* — **plural**. Measured over the other ten
entries:

    narrowing the scan     refused BY NAME, in `parents`' own entry
    degrading an artefact  ABSENT — nothing in the list says it

**One of the two was a precedent and the other was an extension of the same principle**, and the
sentence made them the same kind of thing. **In the one file whose entire subject is not claiming
more than you have**, in the entry its author had just been told to write carefully because he was
the party who introduced the name.

**And the failure mode is the one this register already has a name for.** The claim was not
unchecked — it was *decorated*: a reason beside a number, or here a citation beside a refusal, is
what stops anybody asking whether the citation exists. **Justification as camouflage**, filed
earlier the same day about two contract thresholds, arriving again in prose within hours.

**Restated rather than erased.** The entry now says which of the two is a precedent and which is
an extension, and keeps the prior wording per doctrine rule 4 — because the delta *is* the
finding, and an entry in a list about honest overlaps that quietly corrected its own overclaim
would be the second version of the same act.

*Site:* `evals/oversight/checks.py` :: `    ("height", "height"): (`
*Disposition:* corrected in place. What has no owner is whether the other ten entries cite
precedents that exist — none was checked when they were written, and the same reviewer who found
this one is the reason it is now known that nobody had looked
*Status:* open

---
**A published disagreement count stops at five, and the docstring says *every*** ·
found 2026-09-05 · by `T016`, planting a mutation on the mechanism claim 5 has none for

`evals/definition/checks.py::_disagreements` takes `limit: int = 5` and **breaks out of its loop**
when it reaches it. `compare()` publishes the length of that truncated list as the check's figure:

    figure=f"{len(set(left) | set(right))} cell(s), {len(broken)} disagreeing"

Measured directly, with no pipeline involved — twenty cells, every one of them different:

    20 cells all disagreeing -> 5 reported

The docstring's first line is *"Every cell the two do not agree on, including cells one has and the
other does not."*

**`passed` is unaffected and the claim does not become false**: any disagreement fails the check.
What is wrong is the number beside it, and it is wrong in the flattering direction — a one-cent
disagreement and a catastrophic one publish the same figure. Measured on a planted mutation
(`evals/claim-5-arms-the-sql-mechanism`): **349 cells present in both Python paths and absent from
the SQL, published as `481 cell(s), 5 disagreeing`.**

`evals/README.md`'s fifth rule is *numbers, not a green tick*. Claim 1's `G6` is the contrast: it
publishes `716` and `6,650` as counts and truncates only its examples.

**And the same numbers block hard-codes the cell it constructed.** `("cells", f"{len(sql):,} —
{len(sql) - 1:,} from the corpus, 1 constructed")` subtracts a literal 1 rather than counting. On
the mutated run the SQL had dropped the constructed cell and the line read *"132 — 131 from the
corpus, 1 constructed"* where the truth was 132 and **0** — wrong on exactly the run where the loss
of the eval's own constructed cell is the thing to notice.

**And a check id in prose that no check carries.** `evals/definition/__init__.py` ends a paragraph
*"it is a property of the pipeline, established in `T010` and `T011`, and it is `D5`."* `D5` occurs
**exactly once in the repository**, in that sentence; claim 5 declares `D1`–`D4` and the drop it
describes is published as a number. `make figures`'s `armed-or-says-why` row enumerates `Check(...)`
ids, so a check named only in prose is outside every population.

*Site:* `evals/definition/checks.py` :: `    limit: int = 5,`
*Site:* `evals/definition/checks.py` :: `        ("cells", f"{len(sql):,} — {len(sql) - 1:,} from the corpus, 1 constructed"),`
*Site:* `evals/definition/__init__.py` :: `it is a property of the pipeline, established in`
*Disposition:* branch `evals/claim-5-counts-what-it-found` — count every disagreement and truncate
only the examples, derive the constructed-cell count, and either write `D5` or stop naming it
*Status:* open

---
**Claim 5's load-bearing third mechanism owns no mutation — planted here, and it bites** ·
found 2026-09-05 · by `T016`, in a copy of the tree

All three of claim 5's mutations edit `evals/definition/`'s two Python paths:

    01 rounding-lands-on-every-row-instead-of-every-cell  combine_then_aggregate.py
    02 a-float-where-the-contract-says-decimal            aggregate_then_combine.py
    03 a-cell-only-one-source-has-is-dropped              aggregate_then_combine.py

None edits the compiled SQL, `metric_parts`, any compiler or `pipelines/gold/`. The eval's own
printed note calls that mechanism **the load-bearing third** *"because it was compiled by a
different mechanism at a different time"*, and it is the one nothing has been shown to catch.

**Planted, in a copy of the tree: the same misreading mutation 03 plants on the Python side.**
`metric_parts`'s `left join` read as an inner join — `join: full_outer_on_grain` in the contract
read as an intersection — then regenerated so that compiler and artefact agree:

    before regenerating   holdout-contracts check   FAILED 4 violation(s)  [stale_artefact]
    after regenerating    holdout-contracts check   OK 15 artefact(s) · every byte matches
                          python -m evals.definition
                            FAIL D1.integer-equal  481 cell(s), 5 disagreeing
                            FAIL D2.integer-equal  481 cell(s), 5 disagreeing
                            RED 2/4

**Two things follow and the first is good news.** `make contracts` is green on a compiler that is
wrong, because it compares bytes against a recompile and a wrong-but-consistent compiler agrees
with itself — which is exactly the gap claim 5 exists to fill, now demonstrated rather than argued.
**And claim 5 does bite there**, so arming it costs one YAML file and no new code.

*Site:* `evals/definition/__init__.py` :: `**The SQL is the load-bearing third for exactly that reason**`
*Disposition:* branch `evals/claim-5-arms-the-sql-mechanism` — a mutation against `metric_parts`
under `claim-5`, with the regeneration step in its own `breaks:` so the mutation is honest about
what it needs
*Status:* open

---
**A check landed unarmed four days after the rule that says nothing lands unarmed** ·
found 2026-09-05 · by `T016`, comparing `make gate-proof` with `PLAN.md`'s landing note

`make gate-proof` prints **37 armed · 23 declared un-armable · 8 unarmed**. `PLAN.md`'s landing
note for `evals/unarmed-checks`, 2026-08-31, records **7**. The set differs by exactly one:
`D4.tool-definition-matches-the-contract`, from claim 5, landed 2026-09-04.

`evals/README.md` says of the mechanism that prints those three states:

> *this is what applies it, and what stops the next one being written from prose.*

**The next one was written from prose.** The gate prints and does not refuse, deliberately and for
a stated reason — *refusing it would buy a sentence where a mutation belongs* — and that reason is
sound. What is false is the clause claiming it stops anything.

`D4` is armable: a mutation to the compiled agent tool's declared rounding would break it, and it
carries no `unarmed_because`. The other seven are the phase-1 set less `G7`: `C5`, `C9`, `G4`,
`G6`, `G8`, `U5`, `U9`.

*Site:* `evals/definition/checks.py` :: `        id="D4.tool-definition-matches-the-contract",`
*Disposition:* branch `evals/d4-is-armed-or-says-why`. The clause in `evals/README.md` is the
other half and belongs in the same change: a gate that prints does not stop anything, and the
sentence should say what it does
*Status:* open

---
**The floor a required check rests on is one below what exists, and the sentence that says a gate prevents it points the other way** ·
found 2026-09-05 · by `T016`, running `discover`'s own numbers

    uv run python -c "from ops import figures; print(figures.discover_floor(), figures.claim_targets_that_exist())"
    8 9

`ci.yml`'s `discover` refuses below `FLOOR=8`. Nine targets exist. The floor moved 6 → 7 with
`silver` and 7 → 8 with `gold`; **`claim-5` landed on 2026-09-04 and it did not move.** The
comment beside it says *"FLOOR is what exists today"*.

The same comment says *"`make figures` checks this number against the Makefile, so it cannot go
stale downward."* `ops/figures.floor_failures` refuses only `floor > exists` — its own docstring is
honest about that, and the workflow comment is not.

Measured, by renaming one target at a time in a copy of the Makefile:

    claim-5 / gold / silver / gate-proof renamed away
      discover finds 8 · floor 8 · discover refuses: no · make figures refuses: no

`claims-complete` aggregates only what `discover` emits, and it is one of the three contexts the
`main` ruleset requires.

**The number that argues against this:** three of the four are caught elsewhere — a renamed `gold`
or `silver` by `figures.unrun_target_failures`, a renamed `claim-N` by `tests/evals/test_ledger.py`.
The floor is the backstop for what those miss, and it is the one that is short.

*Site:* `.github/workflows/ci.yml` :: `          FLOOR=8`
*Site:* `ops/figures.py` :: `    if floor > exists:`
*Disposition:* branch `ops/the-floor-is-what-exists` — the floor to nine in the same change that
decides whether `make figures` refuses the other direction, and the workflow comment corrected to
what the check does
*Status:* open

---
**Four deferrals are closed in the registry's prose and counted open by the gate** ·
found 2026-09-05 · by `T016`, scanning every entry for a closure the parser cannot read

`make expiry` reports `36 entr(y/ies) in the section: 31 open, 5 closed`. `ops/expiry.py` reads one
marker, `*Closed:* YYYY-MM-DD`. Four entries record a full closure in bold prose instead:

    docs/SCENARIO.md and docs/DAY-ONE.md                        "Closed 2026-09-02 by T015"
    No threshold at which a reconstruction stops being usable   "Closed 2026-09-04 by T014"
    The censoring correction has no consumer                    "Closed 2026-09-04 by T014"
    No source has declared what stocked_out_from_hour means     "Closed 2026-09-04"

Nine closures are written in the file and the gate reads five. **The true open count is 27, not
31**, and *oldest condition-only deferral is 8 day(s) old* is computed over a population four
entries too large.

**The gate is `ops/expiry-knows-what-closed`, written on 2026-08-31 for exactly this** — phase 1's
§2a. It was correct, published, and every closure written since has used the other spelling. That
is the branch's own lesson — *a new rule is not applied to what already exists unless somebody runs
it there* — pointing forwards instead of backwards.

**Two entries a looser parser would close wrongly**, stated because a coverage question has two
directions: *One pooled availability curve per world* says *"the entry stays open on its own terms
and that is the point of it"*, and *The regulated basket's benchmark* says *"half of this closed"*.
Reading `**Closed` as a marker would take both.

*Site:* `ops/expiry.py` :: `_CLOSED = re.compile(`
*Site:* `docs/DECISIONS.md` :: `> **Closed 2026-09-04 by T014. It has a consumer, and the composition is what the tests assert.**`
*Disposition:* branch `ops/a-closure-is-read-however-it-is-written` — and the choice between
teaching the parser the prose form and rewriting four entries into the marker is the branch's, with
the two half-closures planted against in both directions
*Status:* open

---
**`make language` reproduces the instance its own comment records** ·
found 2026-09-05 · by `T016`, putting a worktree where this tree invites one

`ops/language.py::content_files` walks the working directory and excludes a hand-kept
`NOT_CONTENT`. Its comment counts three instances of what that costs — `.shards/`, *"a stray
worktree that reddened one laptop and no runner"*, and `.terraform/` — and names the fix without
taking it: *the population it ought to be computed from is what git tracks.*

Measured, by creating a git worktree at `.claude/worktrees/phase-2-integration`, a directory that
exists on disk in this tree, untracked and absent from `.gitignore`:

    make language  →  304+ offences, every one inside the worktree copy, exit 1

Every entry in `EXCEPTED_PATHS` is repo-relative, so the copy's
`.claude/worktrees/…/contracts/guardrails/prior_price.yaml` is a different path and the verbatim
Greek law inside it reads as a violation.

**The worktree instance is already on the module's own list, and the list was never given an entry
for it**, so the second worktree reproduces the first exactly. `ops/figures._layout_population`
asks git, one module along in the same package, for the same reason.

The worktree was moved outside the repository and `make language` is green again.

*Site:* `ops/language.py` :: `        ".terraform",`
*Disposition:* branch `ops/language-asks-git-too`. Either the population comes from `git ls-files`
like the layout one, or `.gitignore` gains `.claude/worktrees/` — and the first is the fix the
module already names
*Status:* open

---
**A package says it has four consumers and lists five, one file from where it says five** ·
found 2026-09-05 · by `T016`, counting the bullets

`src/holdout/contracts/compilers/__init__.py` opens *"The four consumers of the metric contract:"*
and is followed by **five** bullets, the fifth being `generated/dashboards/`.
`src/holdout/contracts/compilers/dashboard.py`, in the same package and the same commit, opens
*"A fifth consumer, and the reason it has to be a compiled one is a measurement."*

`docs/FINDINGS.md` already carries *Three consumers named in three files, four emitted*; its three
sites are `CLAUDE.md`, `PLAN.md` and `TASKS.md`, and it was filed before the fifth existed. **This
site is in code, is new, and is the one place a reader goes to find out what compiles.**

*Site:* `src/holdout/contracts/compilers/__init__.py` :: `The four consumers of the metric contract:`
*Disposition:* branch `contracts/the-count-matches-the-list`, and it is a candidate for `PROSE` —
a count in a docstring against `len()` of what the module emits is exactly what that registry is for
*Status:* open

---
**Claim 2 prints two disclaimers that have stopped being true, on every run** ·
found 2026-09-05 · by `T016`, reading the eval's output against the deferral it cites

`evals/README.md`'s sixth rule: *"What this does not prove is printed on every run. Not kept in a
README where it can quietly stop being true."* Two of the five notes in
`evals/uplift/checks.py::report` have:

    "claim 5, with two Python implementations. The dbt model and the SQL function are
     T011 and T012, and the deferral in docs/DECISIONS.md carries them as its unlock"

Both landed on 2026-09-04. Claim 5 exists, is green, and executes the compiled SQL.

    "that the world's prices are certified prices — the guardrail envelope is not on this
     path, and the deferral that says so names phase 2 as its unlock"

The deferral names **T003** — *"T003 is the first eval to run a whole system over a world and is
where the question becomes concrete"* — which landed on 2026-08-28; its condition is *the decision
path being exercised end to end against a world*, which is phase 3's `run`. **Three statements
about one deferral and no two of them agree**, and one of the three is printed by the claim.

`docs/DECISIONS.md` already carries the rule for the middle one — *a prediction about what a task
will touch is not an event in the repository* — written on 2026-09-04 about a different entry and
never swept over this one.

*Site:* `evals/uplift/checks.py` :: `            "this path, and the deferral that says so names phase 2 as its unlock",`
*Site:* `docs/DECISIONS.md` :: `*Unlock condition:* the decision path being exercised end to end against a world, which is`
*Disposition:* branch `evals/the-printed-disclaimer-is-re-read` — both notes corrected against what
runs, and the deferral's forecast sentence restated per doctrine rule 4
*Status:* open

---
**Two packages state their claim standing and the statements are the wrong way round** ·
found 2026-09-05 · by `T016`, asking which packages an eval imports

`pipelines/ingest/__init__.py` set the standard in its own words: *"A module that serves no claim
and says so is a different object from one that serves no claim and does not."* Measured against it:

    pipelines/ingest/   no eval          says "It serves no claim"                  correct
    pipelines/silver/   claim 5's eval   says "It serves no claim ... the layer
                                         they are eventually computed over"         false since 2026-09-04
    pipelines/gold/     claim 5's eval   says nothing                               carries a mechanism
    pipelines/ml/       no eval          says nothing                               the second kind

`evals/definition/build.py` imports `pipelines.silver.build` and `pipelines.gold.build` and runs
both on every `make claim-5`. **The package genuinely upstream of the comparison declares it serves
no claim; the package that materialises claim 5's third mechanism declares nothing.**
`pipelines/ml/` is the second kind exactly as `pipelines/ingest/` defines it, and phase 1's §4
finding about `pricing/selection.py` is still `adrift` against the same shape.

*Site:* `pipelines/silver/__init__.py` :: `evidence itself. The one exception is negative`
*Site:* `pipelines/gold/__init__.py` :: `The one rule this layer is really about`
*Site:* `pipelines/ml/__init__.py` :: `Two things this package is not`
*Disposition:* branch `pipelines/each-package-says-what-it-serves` — three sentences, no code, and
the distinction worth writing down is *on a claim's execution path* against *part of a claim's
evidence*, which silver and gold sit on opposite sides of
*Status:* open

---
**The corpus barrier's runtime half knows one of the two spellings its source half declares** ·
found 2026-09-05 · by `T016`, attacking the barrier with eleven shapes

`ops/isolation.py` declares both spellings and says why — *"A barrier that misses the spelling its
own task description used is not a barrier."* The runtime half, the test written to close the
dynamic hole reading cannot see, passes one:

    block_imports(FORBIDDEN, evict=(POLICED,))

Measured:

    _Refuse(("holdout",))._blocks("holdout.core.money")       True
    _Refuse(("holdout",))._blocks("src.holdout.core.money")   False

    with that finder installed, exactly as the test installs it:
      importlib.import_module("holdout.core.money")      ModuleNotFoundError: blocked for this test
      importlib.import_module("src.holdout.core.money")  <class 'src.holdout.core.money.Money'>

So a **module-level** `importlib.import_module("src.holdout…")` in a corpus module is invisible to
both halves: to `offences`, because there is no `Import` node, and to the runtime test, because the
finder was never told the second spelling.

**And the prose says otherwise.** `tests/boundary/conftest.py`: *"`tests/boundary/test_blocking.py`
plants both spellings against this fixture and requires each to raise."* `src.holdout` occurs
nowhere in `test_blocking.py`; all six of its tests block and plant `holdout`. This is the file
that exists **because** the previous technique's prose looked right.

**What this is not.** It is not the declared hole. `.claude/README.md` and the boundary test both
state that a dynamic import is invisible to the source scan, and the runtime test closes the
module-level half deliberately. What is undeclared is that it closes it for one spelling out of
two, in a repository whose own history records the first spelling costing a barrier.

**Not planted in `corpus/`**, and that is the one step not taken: both halves were measured
directly rather than by writing a file into a checkout other sessions are working in. Each half is
a direct measurement; the composite is inference from them.

*Site:* `tests/boundary/conftest.py` :: `plants both spellings against this fixture and requires each to raise.`
*Site:* `tests/boundary/test_corpus_imports_nothing.py` :: `    block_imports(FORBIDDEN, evict=(POLICED,))`
*Site:* `.claude/README.md` :: `dynamic import taken at import time raises whatever it was spelled as`
*Disposition:* branch `ops/the-barrier-blocks-both-spellings`, first of the eleven proposed —
`block_imports(*FORBIDDEN_ROOTS)`, with `test_blocking.py` planting the second spelling, which is
what its own conftest already claims
*Closed:* 2026-09-05 — by `T00N`. **The composite stopped being inference: the plant ran**, in a
worktree beside the repository rather than in the shared checkout. A `corpus/world/` module doing
a module-level `importlib.import_module("src.holdout.core.money")` bound `Money`, and all four
gates were silent on the same file at once — `offences` `[]`, `scan` `{}`, the hook exit 0, and
`pytest tests/boundary/test_corpus_imports_nothing.py` **40 passed** (39 of them plus the plant's
own parametrisation, which is how the barrier counted it: as one more module it had checked). One word changed to `holdout` and the boundary test failed, so the
two names are separated by the runtime half and by nothing else.

**Two things the finding did not have.** *There is no third route*: `sys.path` carries exactly two
entries inside the tree — `site-packages`, and `src` from `_editable_impl_holdout.pth` — so
`holdout` resolves from `src/`, `src.holdout` from the repository root, and `core` from nothing
(`find_spec("core")` is `None`). Two roots is the whole population, which is worth having measured
rather than assumed of a barrier that declares two. And the prose is at **three** sites, not one;
the third is in `.claude/README.md`'s *what the hooks do not catch, stated rather than assumed*,
where a declared-holes section carried an undeclared hole. Its neighbour at `:51` was re-read and
is correct — right about the half that reads and wrong about the half that runs, four lines apart.

**And the finding overstated its own prose half, which is filed separately against the review.**
The three sentences are ambiguous rather than false: `.claude/README.md` uses *spelling* to mean a
**mechanism** one line below where §13 reads it as a **name**, and under that reading every
sentence quoted is true. What is defective is that one word named two axes — the mechanism an
import is written with, and the name it is written as — so prose true of the covered axis read as
covering the uncovered one. Correcting the wording would not have been enough; the axes are named
apart in all three places, and `test_blocking.py` gains the name axis it never had.
**And the ninth instance of *a value not read off its source* was committed inside the branch
fixing it.** Writing the correction, this session put *"`test_blocking.py` drove **four**
mechanisms"* into the conftest, `PLAN.md` and the commit message. Counted rather than asserted, it
drives **three** — the statement, `__import__`, `importlib.import_module`; the fourth thing in that
sentence is *a lazy loader*, which the conftest lists as something `sys.meta_path` covers and which
no test drives. **The count had been taken off the sentence listing the axis instead of off the
tests driving it — in a branch whose whole subject is a sentence read instead of the thing it
governs.** The family's own shape, committed by the person writing about it, in the file about it.
Caught in the worktree and corrected before the branch left it.

A second, smaller one in the same hour: the plant's result was written as *"`tests/boundary/` 40
passed"* when the command was one file, and the 40 needed its denominator — `main`'s copy of
`test_corpus_imports_nothing.py` collects **39**, so the fortieth was the plant's own
parametrisation. **The barrier counted the planted file as one more module it had checked and
passed on it**, which is the sentence the finding wanted and which a count with no denominator
cannot produce.

*Now:* `tests/boundary/conftest.py` :: `plants each of those against this fixture and requires it to raise, and plants the two *names*`
*Now:* `tests/boundary/test_corpus_imports_nothing.py` :: `    block_imports(*FORBIDDEN_ROOTS, evict=(POLICED,))`
*Now:* `.claude/README.md` :: `of the two names it used. A dynamic import *inside a function* still runs neither check, and`
*Status:* open

---
**A variable's description asserts the absence of the default declared two lines below it** ·
found 2026-09-05 · by `T016`, reading the first layer of the estate

`infra/lakehouse/dashboards.tf`:

    variable "warehouse_id" {
      description = <<-EOT
        ... declared with no default so that a layer applying these resources has to say which
        warehouse rather than inheriting one somebody typed here.
      EOT
      type        = string
      default     = "" # validate-only: T020 supplies the real one
    }

**The default is exactly what removes the protection the description claims.** A `terraform apply`
that forgets `warehouse_id` will not stop; it will bind two dashboards to warehouse `""`.

**And the stated reason does not hold.** Measured, on a copy of the layer with the default removed:

    terraform init -backend=false && terraform validate  →  Success! The configuration is valid.

`terraform validate` does not need it.

This is in the first layer of the estate, in the phase whose whole cost is that mistakes there are
paid for in dollars and in forty-minute applies.

*Site:* `infra/lakehouse/dashboards.tf` :: `  default     = "" # validate-only: T020 supplies the real one`
*Disposition:* branch `infra/the-warehouse-has-no-default` — delete the default, and the
description becomes true. Proposed to land before `T017`, because `T017` is the next thing to touch
`infra/` and a second layer would copy the pattern
*Closed:* 2026-09-05 — by `T00Y`, and **both halves measured on this laptop with Terraform
v1.15.5 rather than inherited from the finding**. With the default gone,
`terraform init -backend=false && terraform validate` still reports *Success! The configuration is
valid.*, and `terraform plan -input=false` **stops**: *"The root module input variable
"warehouse_id" is not set, and has no default value."* So nothing needed the default and something
needed its absence — which is the finding's own claim, run in both directions rather than one.

**And the fix on its own would have been a fix that regresses.** Nothing in this repository read a
`.tf` declaration; `make terraform` runs `validate`, which passed with the default and passes
without it, so the defect was invisible to every gate and would have been re-introduced by the
next person who wanted `validate` to be quiet. `tests/infra/test_variable_declarations.py` is the
guard, and it is a **rule rather than an assertion about `warehouse_id`**: a variable whose
description says it has *no default* may not declare one. A test naming that one variable would
have been a hand-kept population of one and would have said nothing to `T017`, which is the next
layer and the reason this landed first.

**Planted against, because a guard that has never refused anything has not been tested.** Putting
the default back — substitution asserted at one site, and removed again with the count checked —
fails `test_a_variable_that_says_it_has_no_default_declares_none` by name and nothing else.
*Now:* `infra/lakehouse/dashboards.tf` :: `    warehouse rather than inheriting one somebody typed here.`
*Status:* open

---
**An unlock condition fired at `T011` and nobody read it; the route it names is 541 names wide and clean** ·
found 2026-09-05 · by `T016`, reading the registry as a population

> **Claim 7 is proved over `holdout.core` and the contracts, and nothing else exists yet**
> *Unlock condition:* T011, which builds the gold layer.

`T011` landed on 2026-09-04. The entry is unchanged and `make expiry` cannot see it, because it
checks that a condition is present and never that it is true. **It is the only one of the fourteen
task-named conditions whose task has landed and which carries no restatement.**

**Measured, so the exposure is a number rather than an alarm.** `evals/oversight/` scans
`src/holdout/` and `generated/`; `pipelines/` is 30 modules and is scanned by nothing in claim 7.
Running the eval's own reader and its own 317-name lexicon over `pipelines/`:

    1,421 identifiers · 541 distinct names
    collisions with the two published person-vocabularies: 1 — `parents`, at seven sites,
    already on claim 7's explained list for the same reason it is there for src/holdout/

**The route is uncovered and it is clean today**, which is the moment to extend the scan rather
than the moment to worry — and it is what the entry's own text asks for: *the silver tables'
declared schemas and the Lakebase decision record, the two places a customer column would arrive
with a straight face.*

*Site:* `docs/DECISIONS.md` :: `*Unlock condition:* T011, which builds the gold layer.`
*Site:* `evals/oversight/reference.py` :: `PACKAGE = Path(__file__).resolve().parents[2] / "src" / "holdout"`
*Disposition:* branch `docs/the-condition-that-fired-at-T011` for the restatement; whether the scan
extends to `pipelines/` in the same change or in a claim-7 branch is that branch's to decide, and
the measurement above is what it should be decided on
*Status:* open

---
**Three joins on the path phase 3 drives have no implementation and no task** ·
found 2026-09-05 · by `T016`, putting two already-filed halves beside the task registry

`docs/FINDINGS.md` routes three entries to `T016`. Two of them are halves of one thing: `T013`'s
*The single most important screenshot in the project has no data source* and `T014`'s *the adapter
between the model and the decision path has no owner*. **Each was filed by the atom that found it
and each was correct to say it was not theirs.**

Measured:

    Scenario(...) is constructed in     tests/core/test_pricing.py, tests/core/test_composition.py
                                        and nowhere else in the repository
    experiment.close() is called from   evals/assignment/checks.py:852, evals/uplift/harness.py:387
                                        and nowhere else. holdout.core.experiment.readout is
                                        imported by no pipelines/ module — gold imports
                                        assignment and codes, and neither reaches close
    gold.readout is written by          nothing; the compiled dashboard reads `from gold.readout`
    the decision path is composed in    tests/core/test_composition.py and evals/guardrail/build.py;
                                        no pipelines/ module takes a trigger and produces a
                                        certified price or a decision record

**And no task owns any of them.** Phase 3 is six infrastructure layers, the five workflows and a
review; phase 4 is the agent and claim 6. No `closes` in `TASKS.md` names a scenario producer, a
decision-path driver or a readout writer — and `T023`'s `closes` requires the **output** of two of
them: *at least one experiment producing a number and at least one refusing for the right reason.*

**A gap with no owner is the one kind that survives every atom, because every atom can correctly
say it is not theirs.** What nobody did is put the halves beside the registry and ask which atom
owns the wire.

**It does not make a claim untrue.** Claims 1–5 and 7 are proved local and green; none of them
asserts that the system runs end to end, and `CLAUDE.md` has always been careful about that. It
means phase 3's closing condition is not reachable by phase 3's task list, and that this is
knowable now, for nothing.

*Site:* `TASKS.md` :: `title         The five workflows + infra/serving (applied by backfill)`
*Site:* `pipelines/ml/__init__.py` :: `**Units at the price the policy will set. Not units at a candidate price.**`
*Disposition:* the author's, and it is one decision: either the three joins become atoms with ids
placed before `T021`, or phase 3's scope is restated to the demonstration this corpus and this code
can give and the shot list moves with it. `docs/reviews/phase-2.md` §15 carries the argument. It
does not have to be taken today; it has to be taken before `T018`.
**Answered the same day and relayed by `projects-d1`: the corpus gains price randomisation, so
`T023` is not restated — two of the three joins become phase-2 atoms and the third follows the
corpus change, batched with the sub-cent finding.** Left **open** rather than closed, because this
session heard a session that heard the ruling, and because what closes it is the atoms existing
with ids rather than the decision existing
*Status:* open

---
**The `[M]` registry reaches two numbers, and both are a module checking itself** ·
found 2026-09-05 · by `T016`, re-running every present-tense measured figure it could find a command for

`ops/figures.PROSE` is the `[M]` half `docs/reviews/phase-1.md` §8 called *worth more than all the
other corrections together*. It holds two entries, and both recompute a constant from the module
whose docstring asserts it:

    ops/language.py  "uses **<n>** distinct Greek tokens"   len(language.ALLOWED)
    ops/language.py  "outside the <n> excepted paths"       len(language.EXCEPTED_PATHS)

That is a real check and it is not the class §8 was about. Of the six incidents §8 said would have
gone red — the 11/11, the W5 counts, the 100→109→45 chain, *about 36M*, the cache hypothesis —
**none is registered, and neither is any number a claim publishes.** `docs/SCENARIO.md` carries
eight `[M]` tags with the command beside each and no command re-runs them; the docstring says so.

The list's own defence is written down and is good: doctrine rule 4 keeps superseded figures in
`PLAN.md` and `TASKS.md`, so only present-tense text can be registered and which text that is
remains a judgment. **What that defence does not reach is present-tense measured text outside those
two files** — `CLAUDE.md`'s claim rows, the evals' READMEs, the workflow comments. Re-running every
such figure in `CLAUDE.md` by hand found exactly one stale: *17,752 of 17,752*, now 18,069.

**No rule is proposed and no widening.** `CLAUDE.md`'s own argument for waiting applies: a rule
generalised from the forms the known cases wore cannot see the next one, and widening `PROSE` by
hand is the same act as keeping `NOT_CONTENT` by hand. What is recorded is the size of the gap —
**two registered figures against every claim's published numbers** — so the next session finds the
count rather than the impression.

*Site:* `ops/figures.py` :: `PROSE: tuple[Figure, ...] = (`
*Disposition:* was `none` — recorded rather than acted on, deliberately. Overturned by branch `ops/a-published-figure-is-read-off-its-measurement` on **one of its two limbs**
*Closed:* 2026-09-05 — the count limb does not survive re-measurement. It said *one measurement of one stale figure is not grounds to widen `PROSE`*; it was **five figures across thirteen present-tense sites**, one of which (`corpus/real/MANIFEST.yaml`'s 222 fields) had been stale since before this entry was written and was not found by anyone reading. Claim 7's five are now registered and `PROSE` holds **17**. The second limb — *widening it by hand is the same act as keeping `NOT_CONTENT` by hand* — is **not** overturned and is not claimed to be: the list is still kept by hand, still a judgment about which text asserts the present tense, and still prints its own size on every run. What is registered is enumerations computable in 0.02s; claim 2's `8/200` is a sharded 200-draw result that `make check` cannot re-run and stays `[M]` with the command beside it. `src/holdout/contracts/compilers/__init__.py`'s consumer count is still filed separately and still unregistered
*Now:* `ops/figures.py` :: `    # ---------------------------------------------------------------- claim 7's figures`
*Status:* open

---
**Five `CLAUDE.md` lines the author's, one of them a measured figure that has moved** ·
found 2026-09-05 · by `T016`, running the evals behind each figure

`CLAUDE.md` is the author's file. Five lines are named here rather than edited.

| line | measured |
|---|---|
| claim 7's row: *the closed field set refuses **17,752 of 17,752*** | `make eval-oversight` → **18,069 of 18,069**. The other half, *the hand-written list catches 35 of 317*, is exact |
| the layout block: `pipelines/ml/` and `infra/` under *Declared and not yet built* | both built 2026-09-04. `infra` is the only tracked top-level directory named in no other block, so `make figures` reads `layout 23 = 23` off the block that says it does not exist |
| Gold: *the assignment table … is then **read-only*** | `delta.appendOnly` refuses update, delete and overwrite and permits append — three of four — and `pipelines/gold/assignment.py` says so |
| the contract layer: *`contracts/` … **Four families*** | five; `contracts/ml/` landed with `T014` and `TASKS.md` L26 calls it *a fifth contract family* |
| the visible surface: *the figures that matter most — `9/200 = 4.5%`* | the eval has never printed it. `U1` is **8/200 = 4.0%**, which `PLAN.md` and `TASKS.md` carry. Illustrative rather than asserted, and it reads as measured |

*Site:* `CLAUDE.md` :: `the closed field set refuses 17,752 of 17,752`
*Site:* `CLAUDE.md` :: `infra/                 bootstrap · foundation · lakehouse · pipelines · ml · serving`
*Site:* `CLAUDE.md` :: `  then read-only.`
*Site:* `CLAUDE.md` :: `Four families, none of which is a vendor feature.`
*Disposition:* branch `ops/a-published-figure-is-read-off-its-measurement` — was *the author's*, and he delegated all five on 2026-09-05 in the words *do the most professional thing*
*Closed:* 2026-09-05 — all five restated, and the first of them registered so it cannot recur. **The `infra/` restatement moved again on 2026-09-05, when `infra/bootstrap/` landed and made *`lakehouse/` is the only layer that exists* false in the other direction — `make findings` reported `REVERTED` on the closing text rather than letting the correction go stale, which is the whole argument for closure restating a site instead of releasing it. The `*Now:*` below is the second restatement, not the first.** The figure was **not one line**: `18,069` was wrong in `CLAUDE.md`, the `Makefile`, `evals/oversight/README.md` four times and `corpus/real/MANIFEST.yaml`, which was a whole epoch behind. The fifth row had no site of its own and is restated at `CLAUDE.md` :: `that matter most — ``8/200 = 4.0%``` — the number the eval prints, kept illustrative but no longer a figure nobody measured. `SPEC-T003.md`'s `9/200` is **not** touched: a spec written before the measurement is a record of what was asked for, and editing it would rewrite the question
*Now:* `CLAUDE.md` :: `the closed field set refuses 18,069 of 18,069.`
*Now:* `CLAUDE.md` :: `infra/                 Terraform. **Two layers exist**: `bootstrap/` — state backend, OIDC,`
*Now:* `CLAUDE.md` :: `  then **append-only**. `delta.appendOnly` refuses an update, a delete and an insert overwrite,`
*Now:* `CLAUDE.md` :: `6 rest on. Five families, none of which is a vendor feature.`
*Status:* open

---
**An explanation that pre-approves the collision it explains, now five of twelve** ·
found 2026-09-05 · by `T016`, re-measuring the entry routed here

`docs/FINDINGS.md` routes *The explained-collision pair key degrades to the bare identifier* to
`T016`. Re-measured today, after `height` was added:

    12 entries · 5 same-name (agent · candidate · height · members · parents) · 7 differing

**The finding predicted `height` would be a fifth and it is.** The pair protects seven and protects
nothing on five, and the ratio has moved against it.

**No fix is proposed, and the finding's own reason is why**: an explanation keyed to a module, a
type or a line goes stale on a move or an edit, and the pair was chosen because it is stable.

**What costs nothing is publishing the split.** `O12` already re-checks every explanation; printing
*5 of 12 explanations are same-name and pre-approve any future collision on that name* makes the
partiality visible on every run instead of in a register. That is smaller than a fix and it is the
shape this repository uses everywhere else — publish the number that argues against you.

*Site:* `evals/oversight/checks.py` :: `EXPLAINED: dict[tuple[str, str], str] = {`
*Disposition:* branch `evals/the-explanation-publishes-what-it-does-not-cover`. The design question
underneath stays open and unscoped, which is where the entry that raised it left it
*Status:* open

---

## Closed

An entry moves here with its `*Closed:*` line, its original `*Site:*` lines intact, and a `*Now:*`
for each — and it goes on being checked. What closed it has to keep being true.

**This section read *"Nothing yet"* until 2026-09-02.** The first two entries to arrive did so on
the same ruling, on the same day they were filed, which is not the shape anybody expected the
first closures to have: they were filed as *the author's*, and the author answered.

---

**The ingestion gateway Lakeflow Connect requires is classic compute, and it runs continuously** ·
found 2026-09-02 · by T015, from the vendor's own documentation
`CLAUDE.md` routes ERP master data and competitor prices through **Lakeflow Connect**, and its
`backfill` sequence depends on that path. Read 2026-09-02, on two independent pages:

> "The gateway runs on classic compute, and it runs continuously to capture changes before change
> logs can be truncated in the source."
> — [Managed database connectors](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/cdc-overview)

> "must run the gateway as a continuous pipeline. This is critical for PostgreSQL to prevent
> Write-Ahead Log (WAL) bloat … **The minimum requirement is 8 cores**"
> — [Ingest data from PostgreSQL](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/postgresql-pipeline)

**Three sentences in `CLAUDE.md` are contradicted by that**, and the third is the one that hurts,
because it is not an omission but an argument that was made and is wrong:

1. *"Serverless only. **No always-on cluster anywhere in the design.**"*
2. *"there is **no separate EC2 line** — infrastructure is bundled into the serverless DBU rate."*
3. *"The 'you pay Databricks and you pay AWS' trap applies to classic compute, **which this design
   does not use**."* — the design does use it, unavoidably, from the moment the ERP path exists.

**The word `gateway` occurs nowhere in repository content** — grepped across all Markdown on
2026-09-02, excluding gitignored `notes/` and worktrees. The cost table's one classic-shaped line,
*"jobs compute — silver, gold, training | 10 – 30 USD"*, is scoped to three things the gateway is
not, and an 8-core cluster standing continuously from `backfill` to `destroy` adds both a classic
DBU line and the EC2 line sentence 2 says does not exist.

**Three ways out, named because a contradiction presented with two bad options is not a choice.**
None is taken here.

- **Accept it and restate.** The rule becomes *serverless everywhere except the one path a GA
  vendor connector does not offer serverless for*, the cost model gains a line, and doctrine rule 4
  governs the restatement. Honest, and it costs the cleanest sentence in the cost section.
- **Route ERP master data through the S3 bulk load instead**, which `CLAUDE.md`'s repository map
  already declares in `pipelines/ingest/` — *"Zerobus driver · Lakeflow Connect · the S3 bulk
  load"*. **No connector, no gateway, no classic DBU line and no EC2 line.** *And the record
  carries its own argument against it, which is why this is the author's call and not a session's*:
  the ERP is deliberately **driven** during `run` — *"costs change mid-day, a product enters the
  regulated basket, a supplier term changes retroactively, a column is added. A seeded-and-static
  database gives incremental ingestion nothing to do and proves nothing."* A file drop is a
  snapshot; whether the driven day still proves what it is there to prove without change capture is
  the question, and it is a judgment about what the estate is evidence *of*.
- **Hand-write the ingestion.** Explicitly refused already — the sources table chose Lakeflow
  Connect for *"no custom ingestion code to maintain"* — and it is listed only so the refusal is
  visible rather than implicit.

*Site:* `CLAUDE.md` :: `- Serverless only. **No always-on cluster anywhere in the design.**`
*Site:* `CLAUDE.md` :: `serverless DBU rate. The "you pay Databricks and you pay AWS" trap applies to classic compute,`
*Disposition:* **the author's.** Every route changes `CLAUDE.md`, which no session may do and no
two sessions may settle by agreeing. `docs/DAY-ONE.md` §6 records that if the second route is
taken, five of its seven sections stop applying
*Closed:* 2026-09-02 — **the author ruled route 2**: the ERP path becomes files on S3, dropped
several times during `run`, and the connector leaves the design. The contradiction is not
resolved by argument but by removal — there is no gateway, so there is no classic compute, so all
three sentences are true again.
*Now:* `CLAUDE.md` :: `- Serverless only. **No always-on cluster anywhere in the design.**`
*Now:* `CLAUDE.md` :: `serverless DBU rate. The "you pay Databricks and you pay AWS" trap applies to classic compute,`

**Both `*Now:*` lines are the original text, unchanged, and that is what closure looks like
here.** Nothing replaced them because nothing was wrong with them — what was wrong was the design
they described, and the design moved. A finding can close by the world changing under a sentence
that never did.

**And the price is recorded rather than absorbed.** Route 2 buys back *serverless only* by giving
up change capture against a live source: the estate now demonstrates **incremental load of
successive drops**. Smaller, deliberately, and put to the author as smaller.
*Status:* open

---

**Lakeflow Connect is GA; the PostgreSQL connector this estate needs is Public Preview** · found
2026-09-02 · by T015
> "The PostgreSQL connector for Lakeflow Connect is in Public Preview. **Reach out to your
> Databricks account team to enroll in the Public Preview.**"
> — [PostgreSQL connector limitations](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/postgresql-limits), read 2026-09-02

`CLAUDE.md`'s sources table says **(GA)**. Lakeflow Connect *is* GA; **this connector is not**, and
it is the only one the estate's ERP path uses. The two halves of the consequence are different in
kind and are separated deliberately.

**Mechanical, and a fact rather than an opinion.** `make preview-audit` is deferred on the unlock
condition *"the first Terraform layer, and the first time a preview surface is considered"*. **A
preview surface has now been considered.** That half of the condition has fired, and this branch
records it in `docs/DECISIONS.md` rather than leaving it to be noticed. The connector is the first
declared entry the inventory will have.

**And the enrolment is the purest item this repository's day-one document can hold** — a
conversation with a human at a vendor, with a lead time nobody here controls, blocking the entire
ERP path. It is §1 of `docs/DAY-ONE.md` for that reason.

**Judgment, and it is the author's.** Whether this breaches *"No claim depends on a non-GA
surface."* **A reading, with its argument, offered rather than concluded:** probably not, because
all seven claims are provable local with no workspace and no credentials, so the connector sits on
the *estate* path — where proof is captured — and not on any claim's proof path. The counter is
that `run`'s evidence is what the README and the article publish, and evidence resting on a preview
surface is exactly the fragility the rule names. **The two sessions that found this both read it
the first way, which is precisely why it is not settled here.**

*Site:* `CLAUDE.md` :: `| ERP tables, competitor prices | **Lakeflow Connect** (GA) | pull from a database; no custom ingestion code to maintain |`
*Site:* `docs/DECISIONS.md` :: `*Unlock condition:* the first Terraform layer, and the first time a preview surface is considered.`
*Disposition:* the judgment is **the author's**; the mechanical half is recorded on `docs/day-one`
in `docs/DECISIONS.md`, and the enrolment step is recorded in `docs/DAY-ONE.md` §1
*Closed:* 2026-09-02 — **the same ruling, and it closes this one by making the surface
irrelevant rather than by making it GA.** The connector is not used, so nothing in this estate
depends on a Public Preview surface and `CLAUDE.md`'s *(GA)* claim is not merely corrected but
withdrawn along with the row that carried it.
*Now:* `CLAUDE.md` :: `| ERP tables, competitor prices | **bulk load from files on S3** | several drops during the day rather than one: master data changes while the day runs, and no connector, no gateway and no ingestion code to maintain |`
*Now:* `docs/DECISIONS.md` :: `*Unlock condition:* the first Terraform layer, and the first time a preview surface is considered.`

**That second `*Now:*` is the original line, unchanged, and it was nearly written as `gone`** — a
near-miss that turned out to be a hole in the mechanism rather than a slip, and is filed as
*`*Now:* gone` is checked by nothing at all*.

**This is the finding that made the eleven edits impossible to land alone.** `make findings` went
red the moment the sources-table row moved, refusing to let an anchored line change without
somebody saying whether it was fixed or had gone stale. **The ruling and its closure are one
piece of work because the anchor rule makes them one** — which is the register doing exactly what
it is for, on the day it was tested by an edit it had never seen.
*Status:* open

---

**A gate's population is defined by a name prefix, and nothing requires the name** · found
2026-09-03 · by pricing `T010`, and corrected before it landed by reading the twenty lines above
the one it was about

`ops/figures.py`'s `suite` row asks that every test `make test` deselects is selected by some
target CI runs, and it finds those targets by **name**:

    ops/figures.py:532   CLAIM_TARGET_NAME = re.compile(r"^(?P<name>claim-[\w-]*):", re.MULTILINE)

**Nothing requires a target that owns deselected tests to be called `claim-something`.** The
docstring above that line justifies the rule's **breadth** — `claim-` rather than `claim-[0-9]`,
so that `claim-2-shard` and `claim-2-combine` are visible — and says nothing about its
**narrowness**. A target with any other name hands pytest a mark expression that this rule
cannot see, its tests are deselected from the suite, and the row reports them as run by nothing.

**That is the row refusing correctly rather than a gate going quietly wrong**, and it is worth
recording only because of *when* it fires: the first target this repository writes that is not
named `claim-*` and does own marked tests. `T010`'s silver — its tests deselected from the suite,
its work run by a job of its own — is that target, and the row would go red on a branch whose CI
is provably running them.

**What this entry said first, and why the correction is the more useful half.** It read *"two
lists of one population, disagreeing in both directions, and nothing compares them"*, naming
`ci.yml`'s `discover` grep and the line above. **That was false.** `ops/figures.py:98` carries
`ANY_CLAIM_TARGET`, which is `discover`'s pattern arrived at independently, and
`claim_targets_discover_finds` **reads `ci.yml`'s own pattern out of `ci.yml`** and applies it to
the Makefile — so the two enumerations of *the targets CI must invoke* are compared, on every
run, by the `discover` row. The pair I named was not one population enumerated twice: it was two
different questions, and the second one already has the comparison I said was missing.

> **It was written after reading line 532 and line 205, and not the twenty lines above line
> 532.** A claim about what a file does not do, made from the part of it that was open.

The prior wording is recorded here rather than in the file's history because it is an instance of
the family this branch has been counting all day — **a value used without being read off its
source** — and because a finding that was corrected before it landed is worth more as a record of
the correction than as a tidy entry.

**And the second session's confirmation did not open the file either.** The reviewing session
took `CLAIM_TARGET_NAME` from the first session's report, checked `ci.yml`'s `discover` job in
the file, and wrote *"I read `ci.yml`'s `discover` job rather than reasoning from your
description"* — true of one half, and it carried the other half along as though it were true of
both. It then put the false version to the author as fact. **Two-party review, which is the
guard this repository leans on hardest, produced agreement rather than checking**: both parties
had read something, neither had read the twenty lines that mattered, and the agreement felt like
verification. It is `concurred is not closed` arriving one step earlier — at the point where a
finding is *believed* rather than where it is retired.

**What the fix would enumerate, measured before it is written.** Of the **32** targets in the
Makefile, exactly **two** hand pytest a mark expression: `test` (`not claim_2`) and
`claim-2-tests` (`claim_2`). So a rule that asked *which targets select a mark* — reading the
recipes rather than the names — returns exactly what `claim_selection()` returns today, and
would have covered `claim-2-tests` without anyone naming it. **It is a no-op on this tree and
load-bearing on the next one**, which is the only shape of change that can be trusted here.

**The flip side of that rule is named rather than left to be discovered.** A target matching it
that CI never invokes would let the row report coverage from something that never fires — this
defect one flip over. Closing that means asserting that every mark-owning target is one `ci.yml`
emits, derived by `figures`' own route from that file, the way it already reads the discovery
pattern and the floor. `CLAIM_2_SHARDS` is not read by `figures` at all: the shard derivation is
re-implemented, declared as a second implementation, in `tests/ops/test_ci_sharding.py`.

*Site:* `ops/figures.py` :: `CLAIM_TARGET_NAME = re.compile(r"^(?P<name>claim-[\w-]*):", re.MULTILINE)`
*Site:* `ops/figures.py` :: `#: Every target whose recipe may own tests the suite has given up. `
*Disposition:* `T010`'s branch, which is the first thing to exercise it — the rule has to learn
about targets it cannot name in advance, and doing that on a branch with a red row to fix is the
only way to know the change works. **Not closed by the branch that filed it**
*Closed:* 2026-09-03 — by `pipelines/silver`, through the exercise rather than around it. The
rule now reads **recipes instead of names**: `mark_owning_targets` asks every target in the
Makefile what its recipe hands pytest, so `silver` entered the population by existing and
nothing has to be named in advance. Measured at the moment it changed — of 32 targets exactly
two select a mark, `test` and `claim-2-tests` — so the new rule returned precisely what the old
one returned, and then went to three the moment `silver` was written.
**And the flip side is closed with it rather than left open**: `unrun_target_failures` asserts
that every mark-owning target is one `ci.yml` emits, with both sides derived — the recipes on
the left, the workflow's own pattern and its `_SHARDS` derivation on the right — and an empty
left side raising rather than passing vacuously.
*Now:* `ops/figures.py` :: `ANY_TARGET_NAME = re.compile(r"^(?P<name>[a-z][\w.-]*):", re.MULTILINE)`
*Now:* `ops/figures.py` :: `#: Every target in the Makefile, by name, so each can be asked what its recipe does.`
*Status:* open

---
**A mutation's printed output, recorded in three files, and the population under it moved** ·
found 2026-09-05 · by `ops/a-published-figure-is-read-off-its-measurement`, registering the
population that mutation counts

`O2`'s figure is `len(FIELDS_ON_THE_DECISION_PATH) - len(offences)` over the same denominator, so
planting one offence prints `N-1/N`. Three files record that output as **`FAIL O2 · 55/56 types
agree`**, written when the registry held 56. It holds **57**, so the same plant prints `56/57`
today.

**Not restated, and the reason is the distinction this branch is about.** These are not
present-tense assertions about what exists — they are records of what a specific mutation printed
on a specific day, which doctrine rule 4 keeps. `PLAN.md`'s is the one that reads closest to the
present tense (*"putting the registry back gives …"*), and it is still a narrative of a run rather
than a claim about today.

**What is worth the entry is that nothing distinguishes them.** A registered figure and a recorded
one look identical in prose, and the only thing separating them is a judgment made by whoever
writes the sentence. `ops/figures.PROSE` cannot register a mutated-state output — its producer
would have to plant a break, which is `gate-proof`'s mechanism and not `figures`' — so this class
of figure has **no instrument at all**, in either direction.

*Site:* `PLAN.md` :: `set — and putting the registry back gives `FAIL O2 · 55/56 types agree`. The tenth form of the rule`
*Site:* `TASKS.md` :: `                  FAIL O2 · 55/56 types agree.`
*Site:* `docs/DECISIONS.md` :: `> `FAIL O2.every-decision-path-type-carries-exactly-the-fields-written-down — 55/56 types agree``
*Disposition:* none — recorded rather than acted on. Restating a record would be the defect rule 4
names, and registering it needs a mechanism that plants a mutation to compute a figure, which no
gate here has. The candidate owner is `gate-proof`, whose ledger already knows which mutation
targets which check
*Status:* open

---
**Four entries wrote a status this register does not have, and the parser read it as nothing** ·
found 2026-09-05 · by `holdout-98` reading `#62` hostilely, then twice measured

*Site:* `ops/findings.py` :: `_STATUS_LOOSE = re.compile(r"^\*Status:\*[ \t]*(?P<what>\S+)", re.MULTILINE)`
*Disposition:* branch `ops/a-published-figure-is-read-off-its-measurement`
*Closed:* 2026-09-05 — `parse()` refuses a `*Status:*` value that is not `open` or `concurred`,
and refuses an entry with none. The four are corrected to `open` and the three missing ones now
have a line. `test_concurred_cannot_be_spelled_as_closed` keeps its name, its subject and its
docstring's first sentence, and its assertion moves from *accepted and counted open* to *refused*
*Now:* `ops/findings.py` :: `_STATUS_LOOSE = re.compile(r"^\*Status:\*[ \t]*(?P<what>\S+)", re.MULTILINE)`
*Status:* open

**`*Status:*` has two values, `open` and `concurred`, and `closed` is not one of them.** It is the
**agreement** axis — doctrine's *a finding does not close because two sessions agree* is the whole
reason it exists — and `*Closed:*` is the **fix** axis. `is_open` reads only the second. Four
entries wrote `*Status:* closed` anyway; `_STATUS` matched nothing, `status` came back `None`, the
entry passed, and **the gate never said a word.** A value the parser could not read, read as
nothing. Three more entries carried no status line at all, with the same silence.

```
main, 89 entries · 9 with *Closed:*
  *Status:* closed  4     <- a value this field does not have
  *Status:* open    3     <- correct: closed on one axis, unagreed on the other
  no line           2
```

> **RESTATED 2026-09-05, before merge, because the first version of this entry was wrong at the
> root and the fix built on it was worse.** It was filed as *six entries whose status contradicts
> their own closure*, and the fix made `closed` a legal status, required it beside every closure,
> and rewrote the three correct `open` entries into it. **Those three were right as written** — a
> closed finding still has an answer on the agreement axis. The change would have made it
> impossible to record that a closed finding had ever been `concurred`, **deleting the one thing
> the field carries**, inside a register whose own doctrine is that agreement is not closure.
>
> **The prior wording is not kept as prose because it was never a true statement of the defect**,
> and rule 4 preserves superseded *statements*, not a misreading of a format. What is kept is the
> account of it, here, in the entry it belongs to.
>
> **Three things went wrong and only one of them was the report.** It was raised with a
> consequence that did not exist — that the gate miscounts the open set, and that
> `docs/reviews/phase-2.md` §7's `72 · 64 open` is wrong by three. I measured that and refuted
> it. **Then I built the fix on the half I had not measured**, which was the claim that the two
> fields are one axis, and I overturned a test that says the opposite in its own name. **The
> author of the report caught it, against his own finding, before it merged.**

**The reframing survives and belongs to the four.** *The machine-facing half stayed correct and
the human-facing half drifted, invisibly, precisely because no count moved.* A miscount announces
itself the moment somebody adds up; this did not, and could not. **A status value the parser
cannot see is worse than one it disagrees with**, and it is the same shape as the `grep -P` that
exited 1, the `claim-[1-7]` that could not see a `claim-8`, and the `fifty-six` this branch had to
teach `_as_int` to read.

---
**`CLAUDE.md` described five workflows for the whole of phase 2 and one existed** ·
found 2026-09-05 · by the author asking to run a deploy

`.github/workflows/` holds **`ci.yml` and nothing else.** `CLAUDE.md` named *the five workflows*
in the layout block's **what exists today** half, and carried a table of all five in the present
tense under its own heading. **Both were read by every session for the length of a phase.**

**Nothing could have caught it, and the reason is the sharp part.** `make figures` enumerates
top-level directories and packages under `src/holdout/`, so `.github/` was covered **as a
directory** and its contents by nothing at all. The skills table gained a `status` column on
2026-08-31 for precisely this defect — *it listed four skills as living here and one did* — and
that column's own entry in this register says **nothing enumerates this table against
`.claude/skills/`**. It was then given a coverage row. **Nobody extended the idea one directory
sideways**, and `.github/` sat in the same file, four lines away.

**And it was found by somebody trying to use it**, which is the only instrument that was ever
pointed at it: the author asked to run the deploy.

*Site:* `ops/figures.py` :: `        "every *.yml under .github/workflows/",`
*Disposition:* branch `infra/bootstrap-publishes-its-own-trust`
*Closed:* 2026-09-05 — a `workflows` coverage row, mirroring the `skills` pair exactly: the
population is `*.yml` under `.github/workflows/`, the examined side is the rows whose `built`
column says `yes`, and a second check reports a row claiming a workflow that is not there, because
over-claiming is not under-coverage and the one-sided rule cannot see it. Planted: marking
`deploy` as built prints `1 exists / 2 examined` and names `deploy`. Both `CLAUDE.md` sites are
restated with the prior wording kept
*Now:* `ops/figures.py` :: `        "every *.yml under .github/workflows/",`
*Status:* open

---
**A trust anchor that is created and not published leaves a hand-copy nobody wrote down** ·
found 2026-09-05 · by reading `fintelliguard`'s bootstrap workflow

`infra/bootstrap` created `aws_iam_role.deploy` and published its ARN to **SSM**. A workflow
cannot read SSM without first assuming that role, and cannot assume it without naming its ARN —
which carries the account id and therefore cannot be a literal in a public repository. **So the
ARN had to reach a GitHub repository secret, and nothing put it there.**

**The gap is one hand-copy, and a hand-copy into a browser is a console action** — which
`CLAUDE.md` forbids for AWS in the same words it would forbid here: *IaC only. No console
actions, ever.*

**Found in another project's record rather than by reading this one.**
`fintelliguard/.github/workflows/bootstrap.yml` carries the history: an earlier version of it
assumed `secrets.AWS_DEPLOY_ROLE_ARN` in order to run the layer whose whole purpose is to create
that role, and its correction states the rule — ***the trust anchor cannot be derived from the
trust it anchors.*** Its bootstrap writes the secret from inside the local apply.

*Site:* `infra/bootstrap/github.tf` :: `resource "github_actions_secret" "deploy_role_arn" {`
*Disposition:* branch `infra/bootstrap-publishes-its-own-trust`
*Closed:* 2026-09-05 — the layer that creates the role publishes it, so the apply leaves GitHub
able to authenticate and there is no window in which the role exists and the repository does not
know it. The token is read from the environment and never enters the repository, the state or the
configuration; an apply without one fails at plan time, which is correct — a bootstrap that
skipped this silently would report success for a bootstrap that is not one
*Now:* `infra/bootstrap/github.tf` :: `resource "github_actions_secret" "deploy_role_arn" {`
*Status:* open

---
**A per-project layer claimed to own an account-scoped object, and the apply is what said so** ·
found 2026-09-05 · by `terraform apply` failing

`infra/bootstrap` declared `aws_iam_openid_connect_provider.github` as a `resource`. An IAM OIDC
provider is unique **per issuer URL per account**, and this account has had one since 2026-07-04,
created by another project in the portfolio.

```
Error: creating IAM OIDC Provider: EntityAlreadyExists:
Provider with url https://token.actions.githubusercontent.com already exists.
```

**The defect is not the collision; it is the ownership claim.** A layer that creates an
account-scoped object works for whichever project applies first and fails for every one after —
**and the failure is loud only because AWS refuses.** Had two projects each declared it with
different `client_id_list` values, the second apply would have *succeeded* at overwriting a
dependency the first one relies on, with nothing anywhere saying so.

**And the thing being shared is the trust anchor.** `fintelliguard`'s bootstrap comment says *the
trust anchor cannot be derived from the trust it anchors*; this is a second sentence beside it —
**the trust anchor is not per project, and a project that thinks it owns one is wrong about the
account it lives in.**

**And it lands on `CLAUDE.md`'s own checklist, in the entry written for exactly this.** *If the
pattern comes from another project in this portfolio: what problem did it solve there, and do we
actually have that problem?* The OIDC-provider-plus-deploy-role pattern was copied from projects
that apply into this same account — **the pattern was copied and the account was not.** The
bootstrap is right that a project needs a trust anchor and wrong that it owns one, and the
checklist question, asked about the *account* rather than about the *problem*, is what would have
caught it before an apply did.

**Nothing local could have found it.** `terraform validate` reads configuration and does not talk
to AWS, `make terraform` runs exactly that, and this layer's own README says so first: *validate
agrees with almost anything.* **It was found by the first apply**, which is the earliest moment it
could exist — the shape `docs/DAY-ONE.md` already settled for a check that cannot precede the
thing it checks.

*Site:* `infra/bootstrap/oidc.tf` :: `data "aws_iam_openid_connect_provider" "github" {`
*Disposition:* branch `infra/the-trust-anchor-is-shared`
*Closed:* 2026-09-05 — the provider is read by default and created only behind
`create_github_oidc_provider`, so the layer stays complete for an account that has none. What is
read carries a `postcondition` asserting `sts.amazonaws.com` is in its `client_id_list`: another
project owns that list, and without the assertion a change to it would surface as every workflow
failing at `AssumeRoleWithWebIdentity` with this layer green
*Now:* `infra/bootstrap/oidc.tf` :: `data "aws_iam_openid_connect_provider" "github" {`
*Status:* open

