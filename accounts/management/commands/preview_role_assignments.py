"""
Read-only: shows what every SFEmployee *would* get if they logged in right
now, without creating or touching any User (see ADR-009 — real
provisioning happens lazily at login via accounts/provisioning.py, not in
bulk). Useful for sanity-checking a RoleAssignmentRule change before it
affects anyone's next login.
"""

from collections import Counter

from django.core.management.base import BaseCommand

from accounts.role_assignment import resolve_role
from analytics_mirror.models import SFEmployee


class Command(BaseCommand):
    help = "Dry-run report of what resolve_role() would assign every SFEmployee right now. No database writes."

    def handle(self, *args, **options):
        counts = Counter()
        total = 0
        for employee in SFEmployee.objects.all():
            groups, scope = resolve_role(employee)
            key = (", ".join(sorted(g.name for g in groups)) or "(none)", scope)
            counts[key] += 1
            total += 1

        for (group_names, scope), n in sorted(counts.items(), key=lambda kv: -kv[1]):
            self.stdout.write(f"{n:>6}  {group_names}  [{scope}]")

        self.stdout.write(self.style.SUCCESS(f"\n{total:,} employees total (no changes made)."))
