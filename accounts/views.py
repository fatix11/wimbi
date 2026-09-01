from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .dev_users import DEV_USERS
from .session import get_session_user, login_dev_user, logout


def _serialize(user) -> dict:
    return {
        "email": user.email,
        "name": user.name,
        "country": user.country,
        "department": user.department,
        "role": user.role,
    }


@api_view(["GET"])
def list_dev_users(request: Request) -> Response:
    return Response([_serialize(u) for u in DEV_USERS])


# Dev-only stand-in for Keycloak SSO — no credential is actually checked,
# just an email chosen from the fixed dev persona list. Exempt from CSRF
# since it's not a real login. Replace entirely once Keycloak OIDC is wired
# up (ADR-001); the session shape below is what survives that swap.
@csrf_exempt
@api_view(["POST"])
def login(request: Request) -> Response:
    email = request.data.get("email")
    user = login_dev_user(request._request, email) if email else None
    if user is None:
        return Response({"error": "Unknown dev user"}, status=400)
    return Response(_serialize(user))


@api_view(["POST"])
def logout_view(request: Request) -> Response:
    logout(request._request)
    return Response(status=204)


@api_view(["GET"])
def me(request: Request) -> Response:
    user = get_session_user(request._request)
    if user is None:
        return Response({"error": "Not authenticated"}, status=401)
    return Response(_serialize(user))
