from dataclasses import dataclass

from accounts.rbac import can_access_farmer, has_all_country_scope, scope_farmers
from accounts.session import SessionUser


@dataclass
class FakeFarmer:
    country_code: str


malawi_user = SessionUser(
    email="cc.malawi@oneacrefund.org", name="Chikondi Mvula",
    country="MW", department="Call Center", groups=("Call Center",),
)
data_team_user = SessionUser(
    email="data.team@oneacrefund.org", name="Augustin Faraja",
    country="ALL", department="Data & Analytics", groups=("Data Team",),
)

malawi_farmer = FakeFarmer(country_code="MW")
kenya_farmer = FakeFarmer(country_code="KE")


def test_country_scoped_user_can_access_own_country_farmer():
    assert can_access_farmer(malawi_user, malawi_farmer) is True


def test_country_scoped_user_blocked_from_other_country_farmer():
    assert can_access_farmer(malawi_user, kenya_farmer) is False


def test_data_team_user_has_all_country_scope():
    assert has_all_country_scope(data_team_user) is True
    assert can_access_farmer(data_team_user, malawi_farmer) is True
    assert can_access_farmer(data_team_user, kenya_farmer) is True


def test_scope_farmers_filters_by_country():
    assert scope_farmers(malawi_user, [malawi_farmer, kenya_farmer]) == [malawi_farmer]


def test_scope_farmers_does_not_filter_for_data_team():
    assert scope_farmers(data_team_user, [malawi_farmer, kenya_farmer]) == [malawi_farmer, kenya_farmer]
