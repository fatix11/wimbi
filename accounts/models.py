"""
The elastic role-assignment module (see _docs/architectural_decisions.md
ADR-008). RoleAssignmentRule is real, managed, admin-editable data — no
code deploy needed when OAF renames or adds a department.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

ADMIN_GROUP_NAME = "Admin"
GAMMA_GROUP_NAME = "Gamma"


class WorkLocationOperator(models.TextChoices):
    ANY = "ANY", "Any work location"
    EQUALS = "EQUALS", "Work location equals"
    NOT_EQUALS = "NOT_EQUALS", "Work location does not equal"


class RoleAssignmentRule(models.Model):
    """
    One row = one condition mapping an SF department (optionally further
    split by work location) to a *set* of Groups (a department can cover
    more than one persona when the source data can't distinguish them —
    e.g. Business Operations covers both Business Ops and Call Center
    staff, with no field yet to tell them apart) and a data-access country
    scope. Evaluated in `priority` order, first match wins; see
    accounts/role_assignment.py's resolve_role().

    "Admin" can never be a rule target (enforced by the m2m_changed
    receiver below, which fires regardless of whether groups are set via
    the admin UI, a migration, or a shell) — admin-tier access is a
    deliberate, manually-granted trust decision, never something a
    department mapping should be able to hand out on its own.
    """

    department_name = models.CharField(max_length=128)
    work_location_operator = models.CharField(
        max_length=16,
        choices=WorkLocationOperator.choices,
        default=WorkLocationOperator.ANY,
    )
    work_location_value = models.CharField(max_length=128, blank=True)
    groups = models.ManyToManyField(
        "auth.Group", related_name="role_assignment_rules"
    )
    country_scope_override = models.CharField(
        max_length=8,
        blank=True,
        help_text='Leave blank to scope by the employee\'s own country. Set to "ALL" for cross-country access.',
    )
    priority = models.IntegerField(
        default=100, help_text="Lower runs first; the first matching rule wins."
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["priority", "id"]

    def matches(self, employee) -> bool:
        if employee.department_name != self.department_name:
            return False
        if self.work_location_operator == WorkLocationOperator.EQUALS:
            return employee.work_location == self.work_location_value
        if self.work_location_operator == WorkLocationOperator.NOT_EQUALS:
            return employee.work_location != self.work_location_value
        return True

    def __str__(self):
        location = ""
        if self.work_location_operator != WorkLocationOperator.ANY:
            op = "=" if self.work_location_operator == WorkLocationOperator.EQUALS else "!="
            location = f" (WorkLocation {op} {self.work_location_value!r})"
        group_names = ", ".join(self.groups.values_list("name", flat=True)) if self.pk else ""
        return f"{self.department_name}{location} -> {group_names}"


@receiver(m2m_changed, sender=RoleAssignmentRule.groups.through)
def _reject_admin_group_on_rule(sender, instance, action, pk_set, **kwargs):
    """Guardrail for the concern ADR-008 exists to address: no
    RoleAssignmentRule may ever grant "Admin", no matter how the M2M is
    populated (admin UI, shell, migration)."""
    if action != "pre_add" or not pk_set:
        return
    Group = instance.groups.model
    if Group.objects.filter(pk__in=pk_set, name=ADMIN_GROUP_NAME).exists():
        raise ValidationError(
            f'The "{ADMIN_GROUP_NAME}" group can never be assigned by a role rule — grant it manually.'
        )


class WimbiProfile(models.Model):
    """
    Extends Django's own User with the data-access scope resolved from
    the directory (SFEmployee + RoleAssignmentRule, or DEV_USERS — see
    accounts/provisioning.py, ADR-009). Created and refreshed on every
    login via get_or_provision_user() — auth.User is a blank slate
    otherwise, nobody gets an account until they actually log in.
    full_name/department_name are denormalized here so session resolution
    (accounts/session.py) is a single query, not a second lookup back to
    SFEmployee on every request.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wimbi_profile"
    )
    country_scope = models.CharField(max_length=8)  # ISO code, or "ALL"
    sf_email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True, default="")
    department_name = models.CharField(max_length=128, blank=True, default="")

    def __str__(self):
        return f"{self.sf_email} ({self.country_scope})"
