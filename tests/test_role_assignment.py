import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import ADMIN_GROUP_NAME, RoleAssignmentRule
from accounts.provisioning import get_or_provision_user
from accounts.role_assignment import resolve_role
from analytics_mirror.models import SFEmployee

User = get_user_model()


def make_employee(**kwargs):
    defaults = dict(
        email="test@oneacrefund.org",
        full_name="Test Employee",
        department_name="Unmapped Department",
        work_location="Office",
        country_code="MW",
        is_active=True,
    )
    defaults.update(kwargs)
    return SFEmployee.objects.create(**defaults)


def group_names(groups):
    return {g.name for g in groups}


@pytest.mark.django_db
def test_business_operations_maps_to_business_ops_and_call_center(mirror_data):
    employee = make_employee(email="a@oneacrefund.org", department_name="Business Operations")
    groups, scope = resolve_role(employee)
    assert group_names(groups) == {"Business Ops", "Call Center"}
    assert scope == "MW"


@pytest.mark.django_db
def test_field_operations_in_the_field_maps_to_field_officer(mirror_data):
    employee = make_employee(
        email="b@oneacrefund.org", department_name="Field Operations", work_location="Field"
    )
    groups, scope = resolve_role(employee)
    assert group_names(groups) == {"Field Officer"}


@pytest.mark.django_db
def test_field_operations_not_in_the_field_maps_to_field_supervisor(mirror_data):
    employee = make_employee(
        email="c@oneacrefund.org", department_name="Field Operations", work_location="Regional Office"
    )
    groups, scope = resolve_role(employee)
    assert group_names(groups) == {"Field Supervisor"}


@pytest.mark.django_db
def test_it_engineering_gets_data_team_with_all_country_scope(mirror_data):
    employee = make_employee(
        email="d@oneacrefund.org", department_name="IT Engineering", country_code="Kenya"
    )
    groups, scope = resolve_role(employee)
    assert group_names(groups) == {"Data Team"}
    assert scope == "ALL"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "department",
    ["Market Acces", "Rural Retail", "Trees", "Monitoring, Eval & Learning", "Payment for Ecosystem Services"],
)
def test_business_program_departments_map_to_business_program_user(department, mirror_data):
    employee = make_employee(email="e@oneacrefund.org", department_name=department)
    groups, scope = resolve_role(employee)
    assert group_names(groups) == {"Business/Program User"}
    assert scope == "MW"


@pytest.mark.django_db
def test_unmapped_department_falls_back_to_gamma(mirror_data):
    employee = make_employee(email="f@oneacrefund.org", department_name="Legal")
    groups, scope = resolve_role(employee)
    assert group_names(groups) == {"Gamma"}
    assert scope == "MW"


@pytest.mark.django_db
def test_role_assignment_rule_cannot_be_given_the_admin_group():
    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    other_group, _ = Group.objects.get_or_create(name="Some Other Group")
    rule = RoleAssignmentRule.objects.create(department_name="Anything")

    with transaction.atomic(), pytest.raises(ValidationError):
        rule.groups.set([admin_group])

    # A rule that already has legitimate groups can't have Admin mixed in either.
    rule.groups.set([other_group])
    with transaction.atomic(), pytest.raises(ValidationError):
        rule.groups.add(admin_group)


@pytest.mark.django_db
def test_provisioning_preserves_manually_granted_admin_membership(mirror_data):
    employee = make_employee(email="admin.person@oneacrefund.org", department_name="Business Operations")

    user, _ = User.objects.get_or_create(username=employee.email, defaults={"email": employee.email})
    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    user.groups.add(admin_group)

    get_or_provision_user(employee.email)

    user.refresh_from_db()
    names = set(user.groups.values_list("name", flat=True))
    assert {"Business Ops", "Call Center"} <= names
    assert ADMIN_GROUP_NAME in names, "provisioning must never remove a manually granted Admin membership"


@pytest.mark.django_db
def test_provisioning_refreshes_groups_on_every_login(mirror_data):
    """Not just first-login provisioning — a department change should
    take effect the next time the same person logs in."""
    employee = make_employee(email="refresh@oneacrefund.org", department_name="Business Operations")
    user = get_or_provision_user(employee.email)
    assert group_names(user.groups.all()) == {"Business Ops", "Call Center"}

    employee.department_name = "IT Engineering"
    employee.save()

    user = get_or_provision_user(employee.email)
    assert group_names(user.groups.all()) == {"Data Team"}
    assert user.wimbi_profile.country_scope == "ALL"


@pytest.mark.django_db
def test_get_or_provision_user_returns_none_for_unknown_email(mirror_data):
    assert get_or_provision_user("nobody@example.com") is None


@pytest.mark.django_db
def test_dev_user_is_provisioned_on_login(mirror_data):
    user = get_or_provision_user("data.team@oneacrefund.org")
    assert user is not None
    assert group_names(user.groups.all()) == {"Data Team"}
    assert user.wimbi_profile.country_scope == "ALL"
