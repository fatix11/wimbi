"""
Dev-only stand-ins for personas with no real SF department mapping (or
just convenient for local testing) — email -> country/department/group.
Swapped for real Keycloak OIDC once a realm/client exists (ADR-001), and
already resolved through the same accounts/provisioning.py path real
SF-backed employees use (see ADR-009) — a dev login is just a directory
entry that isn't SFEmployee.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DevUser:
    email: str
    name: str
    country: str
    department: str
    group_name: str


DEV_USERS = [
    DevUser(
        email="cc.malawi@oneacrefund.org",
        name="Chikondi Mvula",
        country="MW",
        department="Call Center",
        group_name="Call Center",
    ),
    DevUser(
        email="bizops.malawi@oneacrefund.org",
        name="Thoko Chirwa",
        country="MW",
        department="Business Operations",
        group_name="Business Ops",
    ),
    DevUser(
        email="fieldsupervisor.malawi@oneacrefund.org",
        name="Blessings Gondwe",
        country="MW",
        department="Field Operations",
        group_name="Field Supervisor",
    ),
    DevUser(
        email="data.team@oneacrefund.org",
        name="Augustin Faraja",
        country="ALL",
        department="Data & Analytics",
        group_name="Data Team",
    ),
]


def find_dev_user(email: str) -> DevUser | None:
    return next((user for user in DEV_USERS if user.email == email), None)
