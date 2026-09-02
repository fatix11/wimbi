"""
Session handling on top of Django's real auth system (see ADR-009 — this
used to be a hand-rolled session-cookie key that bypassed
django.contrib.auth entirely; now that real User rows exist via
just-in-time provisioning, there's no reason for a parallel mechanism).
"""

from dataclasses import dataclass

from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import HttpRequest

from .models import WimbiProfile


@dataclass(frozen=True)
class SessionUser:
    email: str
    name: str
    country: str  # ISO code, or "ALL"
    department: str
    groups: tuple[str, ...]


def login_user(request: HttpRequest, user) -> None:
    # No real password check yet (dev-only stand-in for Keycloak SSO, per
    # ADR-001) — user.backend must still be set for login() to work since
    # we're not going through authenticate().
    user.backend = "django.contrib.auth.backends.ModelBackend"
    django_login(request, user)


def logout_user(request: HttpRequest) -> None:
    django_logout(request)


def get_session_user(request: HttpRequest) -> SessionUser | None:
    if not request.user.is_authenticated:
        return None

    if request.user.is_superuser:
        # A bootstrapped superuser (see accounts/provisioning.py's
        # docstring) may have no WimbiProfile at all — default to
        # all-country so they can use the app immediately.
        try:
            profile = request.user.wimbi_profile
        except WimbiProfile.DoesNotExist:
            profile = None
        country = profile.country_scope if profile else "ALL"
        name = profile.full_name if profile else request.user.get_username()
        department = profile.department_name if profile else "Admin"
    else:
        try:
            profile = request.user.wimbi_profile
        except WimbiProfile.DoesNotExist:
            return None
        country = profile.country_scope
        name = profile.full_name
        department = profile.department_name

    return SessionUser(
        email=request.user.get_username(),
        name=name,
        country=country,
        department=department,
        groups=tuple(request.user.groups.values_list("name", flat=True)),
    )
