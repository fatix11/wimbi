"""
Resolves one SFEmployee to (Group, country_scope) via the RoleAssignmentRule
table — see _docs/architectural_decisions.md ADR-008. This is the only
place that logic lives; the sync command and any tests both call through
here rather than re-deriving it.
"""

from django.contrib.auth.models import Group

from analytics_mirror.country_codes import to_iso
from analytics_mirror.models import SFEmployee

from .models import GAMMA_GROUP_NAME, RoleAssignmentRule

PERSONA_GROUPS = [
    "Call Center",
    "Business Ops",
    "Program Executive",
    "Field Supervisor",
    "Field Officer",
    "Data Team",
    "Business/Program User",
]


def resolve_role(employee: SFEmployee) -> tuple[Group, str]:
    """First matching rule wins (ordered by priority). No match -> the
    baseline Gamma group (name borrowed from Superset's own minimal-access
    tier), scoped to the employee's own country either way."""
    for rule in RoleAssignmentRule.objects.select_related("group").all():
        if rule.matches(employee):
            scope = rule.country_scope_override or to_iso(employee.country_code)
            return rule.group, scope

    gamma, _ = Group.objects.get_or_create(name=GAMMA_GROUP_NAME)
    return gamma, to_iso(employee.country_code)


def managed_group_ids() -> set[int]:
    """Groups the automated sync is allowed to touch: every rule target,
    plus the Gamma fallback. "Admin" can never appear here — it can never
    be a rule target (RoleAssignmentRule.clean() enforces that) — so a
    manually-granted Admin membership is structurally never modified."""
    gamma, _ = Group.objects.get_or_create(name=GAMMA_GROUP_NAME)
    ids = set(RoleAssignmentRule.objects.values_list("group_id", flat=True))
    ids.add(gamma.id)
    return ids
