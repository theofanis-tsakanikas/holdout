"""Claim 2 — no uplift without a valid holdout, and on an A/A split the system reports a
significant effect no more often than its declared α.

Run it: `python -m evals.uplift` — or `make claim-2`, which also plants the mutations that
prove each gate bites. `python -m evals.uplift.machinery` is the same named checks at a small
declared configuration, and it is the only module a mutation names.

**Every draw runs the whole system**, not just the estimator: the pre-period covariates, the
nine-field form, feasibility and its automatic exclusions, the committed seed, the stratified
draw, the sealed assignment, exposure read from the corpus's acknowledgements, the four
validity checks and the readout. A formula is not a system, and what claim 2 is about is
whether the machinery around a subtraction preserves a validity the subtraction already had.

The answer to *"your simulator is rigged"* is that validity comes from the lottery and not from
the simulator: a difference of means over randomly assigned units is unbiased under any
data-generating process. That is a theorem. The six worlds do not test the subtraction; they
test the machinery.
"""
