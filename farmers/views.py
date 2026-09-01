from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.rbac import can_access_farmer, scope_farmers
from accounts.session import get_session_user
from analytics_mirror.models import FarmerReach, JourneyEvent, SalesLine


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
    if not query:
        return Response([])

    results = FarmerReach.objects.filter(
        Q(full_name__icontains=query) | Q(gl_client_id__icontains=query)
    )
    scoped = scope_farmers(user, results)
    return Response([_serialize_farmer(f) for f in scoped])


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
