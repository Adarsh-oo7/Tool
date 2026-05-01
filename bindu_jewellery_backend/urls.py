from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth + User management
    path('api/v1/auth/',          include('accounts.urls')),

    # Core apps
    path('api/v1/branches/',      include('branches.urls')),
    path('api/v1/leads/',         include('leads.urls')),
    path('api/v1/calls/',         include('calls.urls')),
    path('api/v1/field-visits/',  include('field_visits.urls')),
    path('api/v1/sales/',         include('sales.urls')),
    path('api/v1/campaigns/',     include('campaigns.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/attendance/',    include('attendance.urls')),
    path('api/v1/reports/',       include('reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
