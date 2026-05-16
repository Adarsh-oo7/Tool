from django.contrib import admin
from .models import FieldVisit, GPSCheckIn, VisitReport


class GPSCheckInInline(admin.TabularInline):
    model           = GPSCheckIn
    extra           = 0
    readonly_fields = ('timestamp',)


@admin.register(FieldVisit)
class FieldVisitAdmin(admin.ModelAdmin):
    list_display    = ('lead', 'staff', 'branch', 'status', 'started_at', 'ended_at')
    list_filter     = ('status', 'branch')
    search_fields   = ('lead__name', 'staff__full_name')
    readonly_fields = ('started_at',)
    inlines         = [GPSCheckInInline]


@admin.register(GPSCheckIn)
class GPSCheckInAdmin(admin.ModelAdmin):
    list_display    = ('visit', 'lat', 'lng', 'timestamp')
    readonly_fields = ('timestamp',)


@admin.register(VisitReport)
class VisitReportAdmin(admin.ModelAdmin):
    list_display    = ('visit', 'outcome', 'time_spent_minutes', 'submitted_at')
    readonly_fields = ('submitted_at',)
