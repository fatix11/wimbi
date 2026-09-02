"""
Row-level access scoping. A session's country scope (either a specific
ISO code, or the "ALL" sentinel) is resolved once at login time (see
accounts/provisioning.py, ADR-009) — this module only ever reads that
value, deliberately independent of which persona/group the session holds
(see _docs/architectural_decisions.md ADR-008's axis separation).
"""

from typing import Iterable, Protocol

from .session import SessionUser


class HasCountryCode(Protocol):
    country_code: str


def has_all_country_scope(user: SessionUser) -> bool:
    return user.country == "ALL"


def can_access_farmer(user: SessionUser, farmer: HasCountryCode) -> bool:
    return has_all_country_scope(user) or farmer.country_code == user.country


def scope_farmers[T: HasCountryCode](user: SessionUser, farmers: Iterable[T]) -> list[T]:
    if has_all_country_scope(user):
        return list(farmers)
    return [farmer for farmer in farmers if farmer.country_code == user.country]
