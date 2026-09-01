"""
Row-level access scoping. "data_team" is the one role with cross-country
scope for the internal pilot (see _docs/business_requirements.md §7); every
other role/persona is scoped to their own country.
"""

from typing import Iterable, Protocol

from .dev_users import DevUser


class HasCountryCode(Protocol):
    country_code: str


def has_all_country_scope(user: DevUser) -> bool:
    return user.role == "data_team"


def can_access_farmer(user: DevUser, farmer: HasCountryCode) -> bool:
    return has_all_country_scope(user) or farmer.country_code == user.country


def scope_farmers[T: HasCountryCode](user: DevUser, farmers: Iterable[T]) -> list[T]:
    if has_all_country_scope(user):
        return list(farmers)
    return [farmer for farmer in farmers if farmer.country_code == user.country]
