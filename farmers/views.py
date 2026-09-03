import datetime
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, render
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.rbac import can_access_farmer, scope_queryset
from accounts.session import get_session_user
from analytics_mirror.models import FarmerReach, JourneyEvent, SalesLine

# A short query (e.g. a single letter) against the real 1.3M-farmer table
# can match a huge fraction of names — materializing that unbounded match
# set crashed the dev server once already (a `q=g` search rendered a
# 113MB response and took the whole process down). Both search endpoints
# push the country scope AND this cap down to the database via a LIMIT,
# rather than filtering/limiting an unbounded list in Python.
MIN_SEARCH_QUERY_LENGTH = 2
MAX_SEARCH_RESULTS = 50


def _search_farmers_queryset(user, query: str):
    return scope_queryset(user, FarmerReach.objects.all()).filter(
        Q(full_name__icontains=query) | Q(gl_client_id__icontains=query)
    ).order_by("gl_client_id")[:MAX_SEARCH_RESULTS]


def _serialize_farmer(farmer: FarmerReach) -> dict:
    return {
        "glClientId": farmer.gl_client_id,
        "name": farmer.full_name,
        "country": farmer.country_code,
        "district": farmer.primary_site,
        "program": farmer.primary_program,
        "joinDate": farmer.onboarded_on,
        "totalSalesLcy": farmer.total_sales_lcy,
        "totalLoans": farmer.total_loans,
        "repaymentRatePct": farmer.repayment_rate_pct,
    }


def _serialize_event(event: JourneyEvent) -> dict:
    return {
        "id": event.pk,
        "glClientId": event.gl_client_id,
        "type": event.event_type,
        "date": event.event_date,
        "program": event.program,
        "amount": event.amount_lcy,
        "currency": event.currency_code,
    }


def _serialize_sales_line(line: SalesLine) -> dict:
    return {
        "id": line.pk,
        "glClientId": line.gl_client_id,
        "date": line.sale_date,
        "productName": line.product_name,
        "productCategory": line.product_category,
        "quantity": line.quantity,
        "unitPriceLcy": line.unit_price_lcy,
        "totalPriceLcy": line.total_price_lcy,
        # Per-line total is null for some real sources (e.g. Kobo tree
        # sales) even though the order it belongs to has a real total —
        # exposed separately rather than silently substituted, so a
        # consumer can decide how to present the distinction (the HTML
        # sales table labels it "(order total)" when it falls back to this).
        "orderTotalPriceLcy": line.total_order_price_lcy,
        "currency": line.currency_code,
        "site": line.site,
        "district": line.district,
        "fieldOfficer": line.field_officer,
        "season": line.derived_season or line.season,
    }


def _get_authorized_farmer(request: Request, gl_client_id: str) -> tuple[FarmerReach | None, Response | None]:
    """Shared guard for every farmer-scoped endpoint: resolves the session
    user and the farmer, and returns an error Response if either auth or
    RBAC fails — callers just return it as-is when non-None."""
    user = get_session_user(request._request)
    if user is None:
        return None, Response({"error": "Unauthorized"}, status=401)

    farmer = FarmerReach.objects.filter(gl_client_id=gl_client_id).first()
    if farmer is None:
        return None, Response({"error": "Not found"}, status=404)
    if not can_access_farmer(user, farmer):
        return None, Response({"error": "Forbidden"}, status=403)

    return farmer, None


@api_view(["GET"])
def search_farmers(request: Request) -> Response:
    user = get_session_user(request._request)
    if user is None:
        return Response({"error": "Unauthorized"}, status=401)

    # NOTE: real V_CLIENT_REACH has no phone number column — search is
    # name/ID only until a phone-bearing source is joined in.
    query = request.query_params.get("query", "").strip()
    if len(query) < MIN_SEARCH_QUERY_LENGTH:
        return Response([])

    results = _search_farmers_queryset(user, query)
    return Response([_serialize_farmer(f) for f in results])


@api_view(["GET"])
def get_farmer(request: Request, gl_client_id: str) -> Response:
    farmer, error = _get_authorized_farmer(request, gl_client_id)
    if error:
        return error
    return Response(_serialize_farmer(farmer))


@api_view(["GET"])
def get_journey(request: Request, gl_client_id: str) -> Response:
    farmer, error = _get_authorized_farmer(request, gl_client_id)
    if error:
        return error

    events = JourneyEvent.objects.filter(gl_client_id=farmer.gl_client_id).order_by("event_date")
    return Response([_serialize_event(e) for e in events])


@api_view(["GET"])
def get_sales(request: Request, gl_client_id: str) -> Response:
    farmer, error = _get_authorized_farmer(request, gl_client_id)
    if error:
        return error

    lines = SalesLine.objects.filter(gl_client_id=farmer.gl_client_id).order_by("sale_date")
    return Response([_serialize_sales_line(line) for line in lines])


# --- HTML pages (ADR-010) ----------------------------------------------
# Additive to the JSON API above, not a replacement — same RBAC helpers,
# rendered as server-rendered templates + HTMX instead of JSON responses.

def _get_farmer_page_or_403(request, gl_client_id: str) -> FarmerReach:
    """HTML-view twin of _get_authorized_farmer: raises Http404/PermissionDenied
    (Django's normal error-page flow) instead of returning a Response,
    since these are template views, not API ones."""
    user = get_session_user(request)
    farmer = get_object_or_404(FarmerReach, gl_client_id=gl_client_id)
    if not can_access_farmer(user, farmer):
        raise PermissionDenied
    return farmer


@login_required
def dashboard_page(request):
    user = get_session_user(request)

    farmers = scope_queryset(user, FarmerReach.objects.all())
    total_farmers = farmers.count()
    total_sales_lcy = farmers.aggregate(total=Sum("total_sales_lcy"))["total"] or 0
    active_programs = (
        farmers.exclude(primary_program__isnull=True)
        .values("primary_program")
        .distinct()
        .count()
    )
    since = datetime.date.today() - datetime.timedelta(days=30)
    recent_activity = scope_queryset(
        user, JourneyEvent.objects.filter(event_date__gte=since)
    ).count()

    by_program = list(
        farmers.exclude(primary_program__isnull=True)
        .values("primary_program")
        .annotate(count=Count("gl_client_id"))
        .order_by("-count")[:10]
    )

    return render(
        request,
        "dashboard.html",
        {
            "total_farmers": total_farmers,
            "total_sales_lcy": total_sales_lcy,
            "active_programs": active_programs,
            "recent_activity": recent_activity,
            "program_labels": [row["primary_program"] for row in by_program],
            "program_counts": [row["count"] for row in by_program],
        },
    )


@login_required
def search_page(request):
    user = get_session_user(request)
    query = request.GET.get("q", "").strip()
    results = []
    too_short = 0 < len(query) < MIN_SEARCH_QUERY_LENGTH
    if len(query) >= MIN_SEARCH_QUERY_LENGTH:
        results = list(_search_farmers_queryset(user, query))
    truncated = len(results) == MAX_SEARCH_RESULTS

    # request.htmx is True for BOTH the live-search partial call (hx-target
    #="search-results") and hx-boost's own full-page navigation (no
    # matching target) — conflating them was the bug: a boosted click on
    # the sidebar's Search link got only the (near-empty) results partial
    # instead of the full page. Only the actual search-results target gets
    # the partial; everything else, boosted or not, gets the full page.
    context = {"results": results, "query": query, "too_short": too_short, "truncated": truncated}
    if request.htmx and request.htmx.target == "search-results":
        return render(request, "partials/search_results.html", context)
    return render(request, "search.html", context)


@login_required
def farmer_profile_page(request, gl_client_id: str):
    farmer = _get_farmer_page_or_403(request, gl_client_id)
    return render(request, "farmer_profile.html", {"farmer": farmer})


@login_required
def journey_partial(request, gl_client_id: str):
    farmer = _get_farmer_page_or_403(request, gl_client_id)
    events = JourneyEvent.objects.filter(gl_client_id=farmer.gl_client_id).order_by("-event_date")
    return render(request, "partials/journey.html", {"events": events})


@login_required
def sales_partial(request, gl_client_id: str):
    farmer = _get_farmer_page_or_403(request, gl_client_id)
    lines = list(SalesLine.objects.filter(gl_client_id=farmer.gl_client_id).order_by("-sale_date"))

    # Some real sources (Kobo tree sales, missing per-unit pricing — see
    # _docs/upstream-gaps.md) have a null total_price_lcy on every line but
    # a real total_order_price_lcy shared across the whole order. Showing
    # that figure on every line would misleadingly read as N separate
    # totals rather than one order total — summarized once per order
    # instead, keyed by source_order_id (falls back to sale_date if that's
    # ever missing).
    missing_price_lines = [
        line for line in lines
        if line.total_price_lcy is None and line.total_order_price_lcy is not None
    ]
    order_key = lambda line: line.source_order_id or str(line.sale_date)
    order_totals = [
        {
            "order_id": order_id,
            "total": group[0].total_order_price_lcy,
            "currency": group[0].currency_code,
            "line_count": len(group),
            "sale_date": group[0].sale_date,
        }
        for order_id, group in (
            (key, list(items))
            for key, items in groupby(sorted(missing_price_lines, key=order_key), key=order_key)
        )
    ]

    return render(request, "partials/sales.html", {"lines": lines, "order_totals": order_totals})
