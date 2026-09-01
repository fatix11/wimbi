from django.contrib import admin

from .models import BridgeClientSourceId, FarmerReach, JourneyEvent, SFEmployee


@admin.register(FarmerReach)
class FarmerReachAdmin(admin.ModelAdmin):
    list_display = ["gl_client_id", "full_name", "country_code", "primary_program", "primary_site"]
    search_fields = ["gl_client_id", "full_name"]
    list_filter = ["country_code", "primary_program"]


@admin.register(JourneyEvent)
class JourneyEventAdmin(admin.ModelAdmin):
    list_display = ["gl_client_id", "event_type", "event_date", "program", "amount_lcy", "currency_code"]
    list_filter = ["event_type", "program"]
    search_fields = ["gl_client_id", "client_name"]


@admin.register(BridgeClientSourceId)
class BridgeClientSourceIdAdmin(admin.ModelAdmin):
    list_display = ["gl_client_id", "source_system", "source_client_id", "match_method"]
    list_filter = ["source_system", "match_method"]
    search_fields = ["gl_client_id", "source_client_id"]


@admin.register(SFEmployee)
class SFEmployeeAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "department_name", "country_code", "is_active"]
    list_filter = ["department_name", "country_code", "is_active"]
    search_fields = ["email", "full_name"]
