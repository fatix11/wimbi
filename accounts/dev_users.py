"""
Dev-only stand-ins for the SuccessFactors-derived identity Keycloak will
eventually provide (email -> country/department/role). Swapped for real
Keycloak OIDC once a realm/client exists (see ADR-001 in
_docs/architectural_decisions.md) — everything downstream (sessions, RBAC)
is built against this same shape, so the swap is a config change, not a
rearchitecture.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DevUser:
    id: str
    email: str
    name: str
    country: str
    department: str
    role: str


DEV_USERS = [
    DevUser(
        id="dev-cc-malawi",
        email="cc.malawi@oneacrefund.org",
        name="Chikondi Mvula",
        country="MW",
        department="Call Center",
        role="call_center",
    ),
    DevUser(
        id="dev-bizops-malawi",
        email="bizops.malawi@oneacrefund.org",
        name="Thoko Chirwa",
        country="MW",
        department="Business Operations",
        role="business_ops",
    ),
    DevUser(
        id="dev-fieldsupervisor-malawi",
        email="fieldsupervisor.malawi@oneacrefund.org",
        name="Blessings Gondwe",
        country="MW",
        department="Field Operations",
        role="field_supervisor",
    ),
    DevUser(
        id="dev-data-team",
        email="data.team@oneacrefund.org",
        name="Augustin Faraja",
        country="ALL",
        department="Data & Analytics",
        role="data_team",
    ),
]


def find_dev_user(email: str) -> DevUser | None:
    return next((user for user in DEV_USERS if user.email == email), None)
