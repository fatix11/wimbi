"""
Walks every SFEmployee, resolves a (Group, country_scope) via
RoleAssignmentRule (see accounts/role_assignment.py, ADR-008), and syncs a
real Django User + WimbiProfile accordingly.

Safe to re-run any time the SF extract or the rule table changes — only
ever touches membership in groups the rule table owns (see
managed_group_ids()), so a manually-granted "Admin" membership is never
disturbed by this command.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import WimbiProfile
from accounts.role_assignment import managed_group_ids, resolve_role
from analytics_mirror.models import SFEmployee

User = get_user_model()


class Command(BaseCommand):
    help = "Assign Wimbi roles and data scope to every SFEmployee (see ADR-008)."

    def handle(self, *args, **options):
        owned_group_ids = managed_group_ids()

        assigned = 0
        with transaction.atomic():
            for employee in SFEmployee.objects.all():
                group, scope = resolve_role(employee)

                user, _ = User.objects.get_or_create(
                    username=employee.email, defaults={"email": employee.email}
                )

                still_owned = user.groups.filter(id__in=owned_group_ids)
                user.groups.remove(*still_owned)
                user.groups.add(group)

                WimbiProfile.objects.update_or_create(
                    user=user, defaults={"country_scope": scope, "sf_email": employee.email}
                )
                assigned += 1

        self.stdout.write(self.style.SUCCESS(f"Assigned roles/scope for {assigned} employees."))
