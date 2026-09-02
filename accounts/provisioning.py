"""
Just-in-time user provisioning, triggered on every login — see
_docs/architectural_decisions.md ADR-009. `auth.User` stays a blank slate
except manually-seeded admin accounts (bootstrap via `createsuperuser`,
then grant "Admin" through the /admin/ UI — no code path here ever
creates one). Everyone else is created the first time they log in, and
has their groups/scope re-resolved from the directory *every* time after
that too, not just once — so access stays current with the rule table and
the SF extract without a separate resync job.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from accounts.dev_users import find_dev_user
from accounts.models import WimbiProfile
from accounts.role_assignment import managed_group_ids, resolve_role
from analytics_mirror.models import SFEmployee

User = get_user_model()


def get_or_provision_user(email: str):
    """Returns the User for `email`, provisioning or refreshing them from
    the directory (SFEmployee, then DEV_USERS) first. If `email` isn't
    recognized by either, returns whatever User already exists for it
    (e.g. a manually-seeded admin with no HR record) or None."""
    employee = SFEmployee.objects.filter(email=email).first()
    if employee is not None:
        groups, scope = resolve_role(employee)
        name, department = employee.full_name, employee.department_name
    else:
        dev = find_dev_user(email)
        if dev is not None:
            group, _ = Group.objects.get_or_create(name=dev.group_name)
            groups, scope = [group], dev.country
            name, department = dev.name, dev.department
        else:
            return User.objects.filter(username=email).first()

    user, _ = User.objects.get_or_create(username=email, defaults={"email": email})

    owned = managed_group_ids()
    user.groups.remove(*user.groups.filter(id__in=owned))
    user.groups.add(*groups)

    WimbiProfile.objects.update_or_create(
        user=user,
        defaults={
            "country_scope": scope,
            "sf_email": email,
            "full_name": name,
            "department_name": department,
        },
    )
    return user
