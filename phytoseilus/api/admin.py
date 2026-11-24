from django.contrib import admin

from .models import ReceivedPredator


@admin.register(ReceivedPredator)
class ReceivedPredatorAdmin(admin.ModelAdmin):
    list_display = (
        "batch_number",
        "supplier_name",
        "number_of_tubs",
        "mortality_rate",
        "status",
        "received_at",
    )
    list_filter = ("status", "received_at", "supplier_name")
    search_fields = ("batch_number", "supplier_reference", "supplier_name")
    readonly_fields = ("mortality_rate",)
