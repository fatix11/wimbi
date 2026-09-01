# Re-seeds RoleAssignmentRule now that `group` (a single FK) became
# `groups` (M2M) in 0003 — one rule can now grant more than one persona's
# groups. Immediate reason: the user learned Call Center staff sit inside
# the "Business Operations" department with no field yet to distinguish
# them from general Business Ops staff, so that rule now grants both
# groups rather than leaving Call Center permanently empty. See
# _docs/architectural_decisions.md ADR-008.
#
# Existing RoleAssignmentRule rows are cleared and recreated fresh — this
# is pre-production configuration data with no dependents worth preserving
# field-by-field across the schema change.

from django.db import migrations

GROUP_NAMES = [
    "Call Center",
    "Business Ops",
    "Program Executive",
    "Field Supervisor",
    "Field Officer",
    "Data Team",
    "Business/Program User",
    "Admin",
    "Gamma",
]

# (department_name, work_location_operator, work_location_value, group_names, country_scope_override)
RULES = [
    ("Business Operations", "ANY", "", ["Business Ops", "Call Center"], ""),
    ("Executive Team", "ANY", "", ["Program Executive"], ""),
    ("Field Operations", "EQUALS", "Field", ["Field Officer"], ""),
    ("Field Operations", "NOT_EQUALS", "Field", ["Field Supervisor"], ""),
    ("IT Engineering", "ANY", "", ["Data Team"], "ALL"),
    ("IT Operations", "ANY", "", ["Data Team"], "ALL"),
    ("Market Acces", "ANY", "", ["Business/Program User"], ""),
    ("Rural Retail", "ANY", "", ["Business/Program User"], ""),
    ("Trees", "ANY", "", ["Business/Program User"], ""),
    ("Monitoring, Eval & Learning", "ANY", "", ["Business/Program User"], ""),
    ("Payment for Ecosystem Services", "ANY", "", ["Business/Program User"], ""),
]


def seed(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    RoleAssignmentRule = apps.get_model("accounts", "RoleAssignmentRule")

    RoleAssignmentRule.objects.all().delete()

    groups = {name: Group.objects.get_or_create(name=name)[0] for name in GROUP_NAMES}

    for department_name, operator, location_value, group_names, scope_override in RULES:
        rule = RoleAssignmentRule.objects.create(
            department_name=department_name,
            work_location_operator=operator,
            work_location_value=location_value,
            country_scope_override=scope_override,
        )
        rule.groups.set([groups[name] for name in group_names])


def unseed(apps, schema_editor):
    RoleAssignmentRule = apps.get_model("accounts", "RoleAssignmentRule")
    RoleAssignmentRule.objects.filter(
        department_name__in={r[0] for r in RULES}
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_remove_roleassignmentrule_group_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
