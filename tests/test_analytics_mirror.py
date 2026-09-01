from analytics_mirror.models import FarmerReach, JourneyEvent


def test_farmer_reach_seeded(mirror_data):
    assert FarmerReach.objects.count() == 6
    grace = FarmerReach.objects.get(gl_client_id="GL-MW-00001")
    assert grace.full_name == "Grace Banda"


def test_journey_events_sorted_chronologically(mirror_data):
    events = list(JourneyEvent.objects.filter(gl_client_id="GL-MW-00001").order_by("event_date"))
    dates = [e.event_date for e in events]
    assert len(dates) > 0
    assert dates == sorted(dates)


def test_farmer_with_no_journey_events(mirror_data):
    assert JourneyEvent.objects.filter(gl_client_id="GL-MW-00003").count() == 0
