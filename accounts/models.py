"""
The elastic role-assignment module (see _docs/architectural_decisions.md
ADR-008). RoleAssignmentRule is real, managed, admin-editable data — no
code deploy needed when OAF renames or adds a department.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

ADMIN_GROUP_NAME = "Admin"
GAMMA_GROUP_NAME = "Gamma"


class WorkLocationOperator(models.TextChoices):
    ANY = "ANY", "Any work location"
    EQUALS = "EQUALS", "Work location equals"
    NOT_EQUALS = "NOT_EQUALS", "Work location does not equal"


class RoleAssignmentRule(models.Model):
    """
    One row = one condition mapping an SF department (optionally further
    split by work location) to a Group and a data-access country scope.
    Evaluated in `priority` order, first match wins; see
    accounts/role_assignment.py's resolve_role().

    "Admin" can never be a rule target (see clean()) — admin-tier access
    is a deliberate, manually-granted trust decision, never something a
    department mapping should be able to hand out on its own.
    """

    department_name = models.CharField(max_length=128)
    work_location_operator = models.CharField(
        max_length=16,
        choices=WorkLocationOperator.choices,
        default=WorkLocationOperator.ANY,
    )
    work_location_value = models.CharField(max_length=128, blank=True)
    group = models.ForeignKey(
        "auth.Group", on_delete=models.PROTECT, related_name="role_assignment_rules"
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

    def clean(self):
        if self.group_id and self.group.name == ADMIN_GROUP_NAME:
            raise ValidationError(
                f'The "{ADMIN_GROUP_NAME}" group can never be assigned by a role rule — grant it manually.'
            )

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
        return f"{self.department_name}{location} -> {self.group.name}"


class WimbiProfile(models.Model):
    """
    Extends Django's own User with the data-access scope resolved from
    RoleAssignmentRule. One row per real, SF-backed user — dev personas
    (accounts/dev_users.py) don't get one; they're a separate, temporary
    path for personas with no real SF mapping yet (e.g. Call Center).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wimbi_profile"
    )
    country_scope = models.CharField(max_length=8)  # ISO code, or "ALL"
    sf_email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.sf_email} ({self.country_scope})"
