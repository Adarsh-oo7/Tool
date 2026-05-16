from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from accounts.views import LoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth endpoints (matched to frontend)
    path('api/v1/auth/login/', LoginView.as_view(), name='auth_login'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='auth_refresh'),
    path('api/v1/auth/logout/', TokenBlacklistView.as_view(), name='auth_logout'),


    # Auth + User management
    path('api/v1/accounts/',      include('accounts.urls')),

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
    path('api/v1/tasks/',         include('tasks.urls')),
    path('api/v1/gamification/',  include('gamification.urls')),
    path('api/v1/marketing/',     include('marketing.urls')),
    path('api/v1/alerts/',        include('alerts.urls')),
    path('api/v1/ai/',            include('ai.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
