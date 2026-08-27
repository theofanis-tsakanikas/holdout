"""The nine-field design form, as frozen dataclasses over plain data.

This mirrors `contracts/design/form.schema.yaml` field for field, and
`tests/core/test_design_form_mirror.py` asserts the mirror against the YAML rather than
against a copy of it. The schema is the source of truth; these types are what the engine
branches on, for the same reason `guardrails/codes.py` writes out a vocabulary the contract
also holds — `holdout.core` may not import a parser or a validator.

The seam, stated so it is deliberate
------------------------------------
**JSON Schema validation of a submitted form does not happen here.** A form arrives at the
engine already parsed and already shape-valid; the module that validates it against
`generated/design/form.schema.json` belongs in `holdout.adapters`. What these types add on
top is the handful of invariants a schema cannot express and the conversions a schema does
not do — most importantly that `Mde.value` is a `Decimal` and never a binary float.

Malformed is not refused
------------------------
`DesignFormError` is raised for a form that is *malformed* — an empty category list, a
non-positive MDE, `weeks` outside 1..52. A refusal is a correct output about a design; an
error is a statement that the caller is wrong, and the two must not be confused. It is the
same split `EnvelopeError` / `Refusal` already makes one package along, and it matters here
because claim 6 counts refusals: an error counted as a refusal would inflate M with things
that were never designs.

`filled_by` is read, recorded, and then ignored
-----------------------------------------------
The engine does not know and does not care who filled the form. All three sources are
first-class, and `tests/core/test_design_engine.py` runs one identical form under all three
attributions and asserts the three results are equal — that is the sentence made checkable
rather than asserted.

One thing that is deliberately **not** refused
----------------------------------------------
`intervention.treatment == intervention.control`. That is an A/A design, and an A/A design
is not a mistake: it is how claim 2 is proved. The whole system runs with the same policy in
both arms, K times, and the rate at which it reports a significant effect must not exceed the
declared α. A form validator that "helpfully" refused it would have made the hardest claim in
the project unbuildable.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

MIN_HYPOTHESIS_CHARS = 30
MAX_HYPOTHESIS_CHARS = 300
MIN_REASON_CHARS = 10
MIN_STORES_WHEN_NAMED = 2
MAX_DURATION_WEEKS = 52


class DesignFormError(ValueError):
    """A form that is malformed rather than infeasible. See the module docstring."""


class Unit(StrEnum):
    """The unit of randomisation.

    It has no single correct answer, which is why a model may propose it — and whether the
    resulting design has the power it claims has exactly one, which is why code decides
    that. Whether a declared carryover fact crosses the dimension a given unit splits arms
    along also has exactly one answer, so code decides that too; the *assumption* it rests
    on is in `contracts/design/inference.yaml`, not here.
    """

    STORE = "store"
    STORE_WEEK = "store_week"
    STORE_CATEGORY = "store_category"
    REGION = "region"


class MdeKind(StrEnum):
    RELATIVE_PCT = "relative_pct"
    ABSOLUTE = "absolute"


class MdeDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    EITHER = "either"


class FilledByKind(StrEnum):
    AGENT = "agent"
    HUMAN = "human"
    POLICY = "policy"


class StoppingKind(StrEnum):
    SINGLE_READOUT_AT_END = "single_readout_at_end"
    GROUP_SEQUENTIAL = "group_sequential"


@dataclass(frozen=True, slots=True)
class FilledBy:
    """Attribution, not a design field — which is why the schema counts it separately."""

    kind: FilledByKind
    name: str | None = None

    def __post_init__(self) -> None:
        if self.kind is FilledByKind.AGENT and self.name is not None:
            raise DesignFormError("the agent is one actor and carries no name")
        if self.kind is not FilledByKind.AGENT and not self.name:
            raise DesignFormError(
                f"a {self.kind.value} attribution names who or what filled the form. "
                "'human' with nobody behind it is an unsigned decision."
            )

    def __str__(self) -> str:
        return self.kind.value if self.name is None else f"{self.kind.value}:{self.name}"


@dataclass(frozen=True, slots=True)
class Intervention:
    """What the two arms actually are.

    Control is never "nothing": the holdout runs the *existing* policy, because comparing
    against abandonment would inflate every uplift. Both are policy refs from the closed
    list the form schema resolves out of `contracts/policies/`.
    """

    treatment: str
    control: str

    def __post_init__(self) -> None:
        if not self.treatment or not self.control:
            raise DesignFormError(
                "both arms name a policy version. A control of 'nothing' is not a control: "
                "the holdout runs the existing policy."
            )

    @property
    def is_a_a(self) -> bool:
        """The same policy in both arms. Not a mistake — it is how claim 2 is proved."""
        return self.treatment == self.control


@dataclass(frozen=True, slots=True)
class Scope:
    """Which categories, products and stores the experiment may touch.

    `products is None` means every product in the named categories, and `stores is None`
    means the whole roster minus the exclusions — the schema's `all`. `None` is the schema's
    own word for *unrestricted*, not an absent fact, which is why doctrine rule 3 has
    nothing to say about it here.
    """

    categories: tuple[str, ...]
    products: tuple[str, ...] | None
    stores: tuple[str, ...] | None

    def __post_init__(self) -> None:
        if not self.categories:
            raise DesignFormError("a scope names at least one category")
        if len(set(self.categories)) != len(self.categories):
            raise DesignFormError("a category appears twice in the scope")
        if self.products is not None:
            if not self.products:
                raise DesignFormError(
                    "an empty product list is not 'every product'. Pass None for that, so "
                    "the two are never confused."
                )
            if len(set(self.products)) != len(self.products):
                raise DesignFormError("a product appears twice in the scope")
        if self.stores is not None:
            if len(self.stores) < MIN_STORES_WHEN_NAMED:
                raise DesignFormError(
                    "a named store list has at least two entries — one store cannot be split "
                    "into two arms. Pass None for the whole roster."
                )
            if len(set(self.stores)) != len(self.stores):
                raise DesignFormError("a store appears twice in the scope")


@dataclass(frozen=True, slots=True)
class Mde:
    """The smallest difference worth detecting, declared in advance.

    Declared afterwards it is whatever the data happened to show, which is why the field is
    required and why the engine sizes against it rather than against anything observed.

    **`value` is a `Decimal`.** The schema says `number`, and PyYAML and `json` both hand
    back a binary float; the adapter converts at the boundary, exactly as the contract layer
    already does. A float reaching `holdout.core` is a lint failure and, one division later,
    a real one.

    **`direction` is required here and optional in the schema, and that is not a default.**
    The schema's own description of the field is *"a one-sided expectation must be declared
    before the period opens or not at all"* — so an absent `direction` in a submitted
    document means the design did not declare one, which is `either`. The adapter reads that
    sentence; this type does not carry the ambiguity forward. Sizing a two-sided design is
    the conservative side of the choice in any case: it asks for more units, never fewer.
    """

    kind: MdeKind
    value: Decimal
    direction: MdeDirection

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise DesignFormError(
                f"an MDE is a Decimal, not {type(self.value).__name__}. A binary float loses "
                "the exactness every downstream comparison here is built on."
            )
        if self.value <= 0:
            raise DesignFormError(
                "an MDE is a positive difference. Zero would mean 'detect anything at all', "
                "which no sample size satisfies."
            )

    @property
    def is_two_sided(self) -> bool:
        return self.direction is MdeDirection.EITHER


@dataclass(frozen=True, slots=True)
class MaxDuration:
    """A business constraint, not a statistical one.

    If the required sample does not fit inside it the design is refused with
    `UNDERPOWERED_FOR_DURATION` rather than quietly shortened. The agent never fills it.
    """

    weeks: int

    def __post_init__(self) -> None:
        if isinstance(self.weeks, bool) or not isinstance(self.weeks, int):
            raise DesignFormError("a duration is a whole number of weeks")
        if not 1 <= self.weeks <= MAX_DURATION_WEEKS:
            raise DesignFormError(
                f"max_duration is between 1 and {MAX_DURATION_WEEKS} weeks; "
                f"{self.weeks} is outside it"
            )


@dataclass(frozen=True, slots=True)
class Exclusion:
    """A store kept out of the experiment, declared before assignment, with its reason.

    Every exclusion is a degree of freedom, so each one carries a reason that can be read
    back — and the set is compared against the locked one at every later moment, which is
    what `EXCLUSIONS_DEFINED_POST_HOC` is about.
    """

    store_id: str
    reason: str

    def __post_init__(self) -> None:
        if not self.store_id:
            raise DesignFormError("an exclusion names a store")
        if len(self.reason.strip()) < MIN_REASON_CHARS:
            raise DesignFormError(
                f"an exclusion carries a reason of at least {MIN_REASON_CHARS} characters. "
                "An exclusion nobody has to justify is a degree of freedom with no cost."
            )


@dataclass(frozen=True, slots=True)
class DecisionRule:
    """What we will do with each outcome, declared before the period opens.

    `if_refused` is mandatory because a refusal is an outcome, and a design with no plan for
    one invites the plan being made after the refusal arrives.

    **This is free text and code does not adjudicate free text.** The engine guarantees three
    non-empty sentences and nothing more; `STOPPING_RULE_PERMITS_PEEKING` is decided over
    `StoppingRule`, a structural value, and never over this prose. What actually stops
    peeking is the readout's refusal to compute before the declared end.
    """

    if_significant: str
    if_not_significant: str
    if_refused: str

    def __post_init__(self) -> None:
        for name in ("if_significant", "if_not_significant", "if_refused"):
            value: str = getattr(self, name)
            if len(value.strip()) < MIN_REASON_CHARS:
                raise DesignFormError(
                    f"decision_rule.{name} must say something. A rule too short to be a "
                    "sentence is a rule that will be written after the result arrives."
                )


@dataclass(frozen=True, slots=True)
class StoppingRule:
    """When the result may be looked at — a structural value, not a sentence.

    It has **no default**. Doctrine rule 3: a default here would be a lie with a plausible
    shape, and the plausible shape is the permissive one — assuming a single readout for a
    design that never said so would make `STOPPING_RULE_PERMITS_PEEKING` unable to fire.

    The design-time check is the announcement. The lock is `readout.may_read`, which refuses
    to compute anything before the declared end whatever anybody declared.

    **A group-sequential rule with no spending function is constructible on purpose.** That
    is exactly the design `STOPPING_RULE_PERMITS_PEEKING` exists to refuse, and a type that
    raised on it would turn a refusal into an error — which is the confusion this module's
    docstring warns about, and which would make the code unreachable in the bargain. What is
    refused here is only structural incoherence: a single readout carrying looks it will
    never take, or a sequential design that admits it will look once.
    """

    kind: StoppingKind
    spending_function: str | None = None
    looks: int | None = None

    def __post_init__(self) -> None:
        if self.kind is StoppingKind.SINGLE_READOUT_AT_END:
            if self.spending_function is not None or self.looks is not None:
                raise DesignFormError(
                    "a single readout at the end has no spending function and no looks. "
                    "Carrying them would describe two different designs at once."
                )
            return
        if self.looks is None or self.looks < MIN_STORES_WHEN_NAMED:
            raise DesignFormError(
                "a group-sequential design declares how many looks it will take, and it is "
                "at least two — one look is a single readout wearing another name."
            )

    @property
    def permits_peeking(self) -> bool:
        """True where the result may be acted on before the declared end with no declared
        spending function.

        Derived rather than stored, so it cannot disagree with the rule it came from. The
        arithmetic is not the point: an interim look without a pre-declared spending
        function inflates the false-positive rate above the declared α *however* the
        estimator is computed, which is why this is decided here and not in the estimator.
        """
        return self.kind is StoppingKind.GROUP_SEQUENTIAL and not self.spending_function


@dataclass(frozen=True, slots=True)
class DesignForm:
    """The nine fields, plus the attribution stamp.

    A human, a declared policy or the agent may fill the nine. The engine does not know and
    does not care which: same checks, same refusals, same experiment.
    """

    hypothesis: str
    intervention: Intervention
    scope: Scope
    primary_metric: str
    unit: Unit
    mde: Mde
    max_duration: MaxDuration
    exclusions: tuple[Exclusion, ...]
    decision_rule: DecisionRule
    filled_by: FilledBy

    def __post_init__(self) -> None:
        length = len(self.hypothesis.strip())
        if not MIN_HYPOTHESIS_CHARS <= length <= MAX_HYPOTHESIS_CHARS:
            raise DesignFormError(
                f"a hypothesis is one precise sentence of {MIN_HYPOTHESIS_CHARS}-"
                f"{MAX_HYPOTHESIS_CHARS} characters; this one is {length}. Imprecision here "
                "is caught by no later check, because every later check takes it as given."
            )
        if not self.primary_metric:
            raise DesignFormError("a design names its primary metric")
        excluded = [e.store_id for e in self.exclusions]
        if len(set(excluded)) != len(excluded):
            raise DesignFormError(
                "the same store is excluded twice, with two reasons. Which one is the reason?"
            )

    @property
    def excluded_store_ids(self) -> frozenset[str]:
        return frozenset(e.store_id for e in self.exclusions)

    @property
    def exclusion_pairs(self) -> tuple[tuple[str, str], ...]:
        """The exclusions as sorted `(store_id, reason)` pairs.

        Sorted, so that two forms that excluded the same stores for the same reasons in a
        different order compare equal. `EXCLUSIONS_DEFINED_POST_HOC` is about the *set*
        having moved, not about the order somebody typed it in.
        """
        return tuple(sorted((e.store_id, e.reason) for e in self.exclusions))

    def canonical_fields(self) -> tuple[str, ...]:
        """Every field, flattened to text, in a fixed order — what a digest is taken over.

        Deliberately written out rather than derived from `dataclasses.fields`. A digest is
        supposed to change when the design changes, so the list of what it covers is a
        decision a reader must be able to check; a derived one would silently start covering
        a tenth field the day somebody added one, which is the moment a reviewer most needs
        to be looking.

        `filled_by` is in it. The engine ignores attribution when deciding, and the digest is
        not a decision: it is the identity of the document, and the same design filled by two
        different people is two documents.
        """
        return (
            "hypothesis",
            self.hypothesis.strip(),
            "treatment",
            self.intervention.treatment,
            "control",
            self.intervention.control,
            "categories",
            "\x1f".join(self.scope.categories),
            "products",
            "*" if self.scope.products is None else "\x1f".join(self.scope.products),
            "stores",
            "*" if self.scope.stores is None else "\x1f".join(self.scope.stores),
            "primary_metric",
            self.primary_metric,
            "unit",
            self.unit.value,
            "mde",
            f"{self.mde.kind.value}:{self.mde.value}:{self.mde.direction.value}",
            "max_duration_weeks",
            str(self.max_duration.weeks),
            "exclusions",
            "\x1f".join(f"{store}={reason}" for store, reason in self.exclusion_pairs),
            "decision_rule",
            "\x1f".join(
                (
                    self.decision_rule.if_significant,
                    self.decision_rule.if_not_significant,
                    self.decision_rule.if_refused,
                )
            ),
            "filled_by",
            str(self.filled_by),
        )
