"""
DRF requires an authentication class to actually adopt Django's own
session-authenticated user — without one, DRF's own (empty) authentication
resolution silently overwrites request._request.user back to
AnonymousUser on every @api_view call, even though AuthenticationMiddleware
already set it correctly moments earlier. See _docs/architectural_decisions.md
ADR-009.

CSRF enforcement is skipped here — not just Django's @csrf_exempt, which
DRF's own SessionAuthentication.enforce_csrf() ignores entirely (a separate
gotcha), but a deliberate choice consistent with this whole auth flow being
a dev-only stand-in for Keycloak SSO (ADR-001), not yet hardened. Revisit
once real auth (or a real CSRF-token flow from the frontend) replaces it.
"""

from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return None
