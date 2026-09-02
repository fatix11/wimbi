from django.views.decorators.csrf import csrf_exempt
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
