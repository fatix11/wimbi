"""HTML pages added under ADR-010 (Django + HTMX) — additive to the JSON
API covered by test_farmers_api.py, same RBAC helpers underneath."""

from accounts.provisioning import get_or_provision_user
from accounts.rbac import scope_queryset
from accounts.session import get_session_user
from analytics_mirror.models import FarmerReach


def login_as(client, email):
    client.force_login(get_or_provision_user(email))


def test_login_page_renders(client, mirror_data):
    response = client.get("/login/")
    assert response.status_code == 200


def test_login_submit_with_known_email_redirects_to_dashboard(client, mirror_data):
    response = client.post("/login/", {"email": "cc.malawi@oneacrefund.org"})
    assert response.status_code == 302
    assert response.url == "/dashboard/"


def test_login_submit_with_unknown_email_shows_error(client, mirror_data):
    response = client.post("/login/", {"email": "nobody@example.com"})
    assert response.status_code == 400
    assert b"Unknown user" in response.content


def test_dashboard_requires_login(client, mirror_data):
    response = client.get("/dashboard/")
    assert response.status_code == 302
    assert "/login/" in response.url


def test_dashboard_scopes_farmer_count_to_country(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert response.context["total_farmers"] == 4  # 4 Malawi fixture farmers


def test_dashboard_shows_all_countries_for_data_team(client, mirror_data):
    login_as(client, "data.team@oneacrefund.org")
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert response.context["total_farmers"] == 6  # all fixture farmers


def test_glossary_page_requires_login(client):
    response = client.get("/glossary/")
    assert response.status_code == 302
    assert "/login/" in response.url


def test_glossary_page_open_to_any_authenticated_user(client, mirror_data):
    """No RBAC gate, unlike the bulk uploader's own dataset pages — this is
    schema/definition reference, not farmer data, so any logged-in user
    (uploader or not) can see it."""
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/glossary/")
    assert response.status_code == 200
    assert response.context["entities"][0]["key"] == "client"
    assert response.context["total_deduped"] < response.context["total_raw"]  # some names are shared
    assert b"loan_product_name" in response.content


def test_glossary_page_marks_shared_variables_with_the_other_entities(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/glossary/")
    client_entity = next(e for e in response.context["entities"] if e["key"] == "client")
    source_client_id = next(v for v in client_entity["variables"] if v["name"] == "source_client_id")
    assert "Sale" in source_client_id["shared_with"]
    assert "Client" not in source_client_id["shared_with"]  # never lists its own entity


def test_search_page_scopes_results_to_country(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/search/", {"q": "GL-"})
    assert response.status_code == 200
    assert {f.country_code for f in response.context["results"]} == {"MW"}


def test_search_page_live_search_request_returns_partial_only(client, mirror_data):
    """The search input's own hx-get (hx-target="search-results") should
    get just the results fragment."""
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get(
        "/search/", {"q": "Grace"}, HTTP_HX_REQUEST="true", HTTP_HX_TARGET="search-results"
    )
    assert response.status_code == 200
    assert b"<html" not in response.content.lower()
    assert b"Grace Banda" in response.content


def test_search_page_blocks_single_character_query(client, mirror_data):
    """A 1-character query against the real 1.3M-farmer table once matched
    a huge fraction of names and crashed the dev server (113MB response,
    broken pipe) — see ADR-010's 2026-09-02 update. Below the minimum
    length, search must not touch the database at all."""
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/search/", {"q": "a"})
    assert response.status_code == 200
    assert response.context["results"] == []
    assert response.context["too_short"] is True


def test_search_page_truncates_at_max_results(client, mirror_data, monkeypatch):
    """Regression test for the same incident: even a query that matches
    more farmers than the cap must never return more than MAX_SEARCH_RESULTS."""
    import farmers.views as farmers_views

    monkeypatch.setattr(farmers_views, "MAX_SEARCH_RESULTS", 2)
    login_as(client, "data.team@oneacrefund.org")  # ALL scope — sees every fixture farmer
    response = client.get("/search/", {"q": "an"})  # matches several fixture names
    assert response.status_code == 200
    assert len(response.context["results"]) == 2
    assert response.context["truncated"] is True


def test_search_page_boosted_nav_returns_full_page_not_partial(client, mirror_data):
    """Regression test: hx-boost on the sidebar's Search link also sets
    HX-Request, but has no hx-target — it must still get the full page
    (with sidebar/title), not the near-empty results partial. This was a
    real bug: clicking Search from the dashboard rendered a blank page."""
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/search/", HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert b"<html" in response.content.lower()
    assert b"Search farmers" in response.content


def test_farmer_profile_page_allows_own_country(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/farmers/GL-MW-00001/")
    assert response.status_code == 200
    assert b"Grace Banda" in response.content


def test_farmer_profile_page_blocks_cross_country_access(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/farmers/GL-KE-00001/")
    assert response.status_code == 403


def test_farmer_profile_page_404s_for_unknown_farmer(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/farmers/GL-XX-99999/")
    assert response.status_code == 404


def test_journey_partial_blocks_cross_country_access(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/farmers/GL-KE-00001/journey/")
    assert response.status_code == 403


def test_sales_partial_renders_for_own_country_farmer(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/farmers/GL-MW-00001/sales/")
    assert response.status_code == 200
    assert b"Hybrid Maize Seed" in response.content


def test_sales_partial_summarizes_order_total_when_line_total_is_null(client, mirror_data):
    """Regression test: found live-testing farmer MW-00008737 (real Kobo
    tree sales, missing per-unit pricing — see _docs/upstream-gaps.md).
    total_price_lcy was null on every line; total_order_price_lcy was
    populated but identical across all lines of the order, so repeating it
    per row (an earlier fix) misleadingly read as N separate totals.
    Summarized once per order instead, and each line's own Total cell
    stays an honest "—"."""
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/farmers/GL-MW-00003/sales/")
    assert response.status_code == 200
    assert b"49088" in response.content
    assert b"upstream-gaps.md" in response.content


def test_logout_page_requires_post(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.get("/logout/")
    assert response.status_code == 405


def test_logout_page_logs_out_and_redirects(client, mirror_data):
    login_as(client, "cc.malawi@oneacrefund.org")
    response = client.post("/logout/")
    assert response.status_code == 302
    assert response.url == "/login/"
    assert client.get("/dashboard/").status_code == 302


def _session_user_for(rf, email):
    # get_session_user only ever reads request.user — no session middleware
    # needed for this unit test, just a request carrying the right user.
    request = rf.get("/")
    request.user = get_or_provision_user(email)
    return get_session_user(request)


def test_scope_queryset_filters_by_country(mirror_data, rf):
    session_user = _session_user_for(rf, "cc.malawi@oneacrefund.org")

    scoped = scope_queryset(session_user, FarmerReach.objects.all())
    assert {f.country_code for f in scoped} == {"MW"}
    assert scoped.count() == 4


def test_scope_queryset_does_not_filter_for_all_country_scope(mirror_data, rf):
    session_user = _session_user_for(rf, "data.team@oneacrefund.org")

    scoped = scope_queryset(session_user, FarmerReach.objects.all())
    assert scoped.count() == 6
