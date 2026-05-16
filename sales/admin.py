from django.contrib import admin
from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display    = ('branch', 'segment', 'product_name', 'amount', 'staff', 'created_at')
    list_filter     = ('branch', 'segment')
    search_fields   = ('staff__full_name', 'lead__name', 'product_name')
    readonly_fields = ('created_at',)
