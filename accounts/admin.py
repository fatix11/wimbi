from django.contrib import admin

from .models import RoleAssignmentRule, WimbiProfile


@admin.register(RoleAssignmentRule)
class RoleAssignmentRuleAdmin(admin.ModelAdmin):
    list_display = [
        "department_name",
        "work_location_operator",
        "work_location_value",
        "group_names",
        "country_scope_override",
        "priority",
    ]
    list_filter = ["groups", "work_location_operator"]
    search_fields = ["department_name", "notes"]
    filter_horizontal = ["groups"]
    ordering = ["priority", "id"]

    @admin.display(description="Groups")
    def group_names(self, obj):
        return ", ".join(obj.groups.values_list("name", flat=True))


@admin.register(WimbiProfile)
class WimbiProfileAdmin(admin.ModelAdmin):
    list_display = ["sf_email", "country_scope", "user"]
    search_fields = ["sf_email"]
    list_filter = ["country_scope"]
