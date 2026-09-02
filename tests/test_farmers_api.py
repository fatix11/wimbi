from accounts.provisioning import get_or_provision_user


def login_as(client, email):
    client.force_login(get_or_provision_user(email))


def test_search_requires_auth(client, mirror_data):
    response = client.get("/api/farmers/", {"query": "Grace"})
    assert response.status_code == 401


def test_search_scopes_to_country(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/api/farmers/", {"query": "GL-"})
    assert response.status_code == 200
    assert {row["country"] for row in response.json()} == {"MW"}


def test_search_finds_farmer_by_name(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/api/farmers/", {"query": "Grace"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["glClientId"] == "GL-MW-00001"


def test_get_farmer_blocks_cross_country_access(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/api/farmers/GL-KE-00001/")
    assert response.status_code == 403


def test_get_farmer_allows_data_team_cross_country(client, mirror_data):
    login_as(client, "data.team@oneacrefund.org")
    response = client.get("/api/farmers/GL-KE-00001/")
    assert response.status_code == 200


def test_get_farmer_not_found(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/api/farmers/GL-XX-99999/")
    assert response.status_code == 404


def test_get_journey_blocks_cross_country_access(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/api/farmers/GL-KE-00001/journey/")
    assert response.status_code == 403


def test_get_journey_returns_sorted_events(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/api/farmers/GL-MW-00001/journey/")
    assert response.status_code == 200
    dates = [row["date"] for row in response.json()]
    assert len(dates) > 0
    assert dates == sorted(dates)


def test_get_sales_returns_line_items(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/api/farmers/GL-MW-00001/sales/")
    assert response.status_code == 200
    lines = response.json()
    assert len(lines) == 1
    assert lines[0]["productName"] == "Hybrid Maize Seed"


def test_get_sales_blocks_cross_country_access(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/api/farmers/GL-KE-00001/sales/")
    assert response.status_code == 403
