from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .dev_users import DEV_USERS
from .provisioning import get_or_provision_user
from .session import SessionUser, get_session_user, login_user, logout_user


def _serialize_session_user(user: SessionUser) -> dict:
    return {
        "email": user.email,
        "name": user.name,
        "country": user.country,
        "department": user.department,
        "groups": list(user.groups),
    }


@api_view(["GET"])
def list_dev_users(request: Request) -> Response:
    return Response(
        [
            {
                "email": u.email,
                "name": u.name,
                "country": u.country,
                "department": u.department,
                "group": u.group_name,
            }
            for u in DEV_USERS
        ]
    )


# Dev-only stand-in for Keycloak SSO — no credential is actually checked,
# just an email that resolves against the directory (SFEmployee, or
# DEV_USERS). Exempt from CSRF since it's not a real login. Replace
# entirely once Keycloak OIDC is wired up (ADR-001); the session shape
# below is what survives that swap.
@csrf_exempt
@api_view(["POST"])
def login(request: Request) -> Response:
    email = request.data.get("email")
    user = get_or_provision_user(email) if email else None
    if user is None:
        return Response({"error": "Unknown user"}, status=400)

    login_user(request._request, user)
    session_user = get_session_user(request._request)
    return Response(_serialize_session_user(session_user))


@csrf_exempt
@api_view(["POST"])
def logout_view(request: Request) -> Response:
    logout_user(request._request)
    return Response(status=204)


@api_view(["GET"])
def me(request: Request) -> Response:
    user = get_session_user(request._request)
    if user is None:
        return Response({"error": "Not authenticated"}, status=401)
    return Response(_serialize_session_user(user))


# --- HTML pages (ADR-010) ---------------------------------------------
# Real Django CSRF protection applies here (no @csrf_exempt) — the login
# form carries {% csrf_token %} and htmx carries it via base.html's
# hx-headers. Same dev-stand-in-for-Keycloak posture as the JSON login
# above: an email that resolves against the directory, no password check.

def login_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard_page")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = get_or_provision_user(email) if email else None
        if user is None:
            return render(request, "login.html", {"error": "Unknown user", "email": email}, status=400)
        login_user(request, user)
        return redirect("dashboard_page")

    return render(request, "login.html")


@require_POST
@login_required
def logout_page(request):
    logout_user(request)
    return redirect("login_page")
