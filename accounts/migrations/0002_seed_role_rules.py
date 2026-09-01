# Seeds the initial elastic role-assignment mapping (see
# _docs/architectural_decisions.md ADR-008) — a one-time bootstrap. From
# here on, the mapping is meant to be maintained via Django admin, not by
# adding more migrations.

from django.db import migrations

GROUP_NAMES = [
    "Call Center",  # no rule maps to this yet — no matching SF department found
    "Business Ops",
    "Program Executive",
    "Field Supervisor",
    "Field Officer",
    "Data Team",
    "Business/Program User",
    "Admin",  # never a rule target — granted manually only
    "Gamma",  # fallback for any department with no rule
]

# (department_name, work_location_operator, work_location_value, group_name, country_scope_override)
RULES = [
    ("Business Operations", "ANY", "", "Business Ops", ""),
    ("Executive Team", "ANY", "", "Program Executive", ""),
    ("Field Operations", "EQUALS", "Field", "Field Officer", ""),
    ("Field Operations", "NOT_EQUALS", "Field", "Field Supervisor", ""),
    ("IT Engineering", "ANY", "", "Data Team", "ALL"),
    ("IT Operations", "ANY", "", "Data Team", "ALL"),
    ("Market Acces", "ANY", "", "Business/Program User", ""),  # sic — matches the real SF data verbatim
    ("Rural Retail", "ANY", "", "Business/Program User", ""),
    ("Trees", "ANY", "", "Business/Program User", ""),
    ("Monitoring, Eval & Learning", "ANY", "", "Business/Program User", ""),
    ("Payment for Ecosystem Services", "ANY", "", "Business/Program User", ""),
]


def seed(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    RoleAssignmentRule = apps.get_model("accounts", "RoleAssignmentRule")

    groups = {}
    for name in GROUP_NAMES:
        group, _ = Group.objects.get_or_create(name=name)
        groups[name] = group

    for department_name, operator, location_value, group_name, scope_override in RULES:
        RoleAssignmentRule.objects.get_or_create(
            department_name=department_name,
            work_location_operator=operator,
            work_location_value=location_value,
            defaults={
                "group": groups[group_name],
                "country_scope_override": scope_override,
            },
        )


def unseed(apps, schema_editor):
    RoleAssignmentRule = apps.get_model("accounts", "RoleAssignmentRule")
    RoleAssignmentRule.objects.filter(
        department_name__in={r[0] for r in RULES}
    ).delete()
    # Groups deliberately left in place on reverse — may already have real
    # users/manual Admin grants attached by the time anyone reverses this.


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
