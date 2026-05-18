from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone


class BaseIntegrationService(ABC):
    """
    Base class for all integration services.
    Provides common functionality for OAuth, token management, and analytics syncing.
    """
    
    def __init__(self, integration):
        self.integration = integration
    
    @abstractmethod
    def connect(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Connect to the platform using OAuth authorization code.
        Returns: dict with access_token, refresh_token, expires_in, account_info
        """
        pass
    
    @abstractmethod
    def refresh_access_token(self) -> str:
        """
        Refresh the access token using refresh token.
        Returns: new access token
        """
        pass
    
    @abstractmethod
    def fetch_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch analytics data from the platform.
        Returns: dict with analytics metrics
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate that the current connection is working.
        Returns: True if connection is valid
        """
        pass
    
    def get_available_properties(self) -> list:
        """
        Optional: Fetch all available properties/accounts under this integration.
        Returns a list of dicts with 'id', 'name', and 'account_name'.
        """
        return []

    def is_token_expired(self) -> bool:
        """Check if the access token is expired or will expire soon."""
        if not self.integration.token_expiry:
            return False
        # Consider token expired if it expires within 5 minutes
        expiry_threshold = timezone.now() + timedelta(minutes=5)
        return timezone.now() >= expiry_threshold
    
    def should_refresh_token(self) -> bool:
        """Check if token needs to be refreshed."""
        return self.is_token_expired()
    
    def sync_analytics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Sync analytics data from the platform to the database.
        This is the main sync method that handles the entire sync process.
        """
        from campaigns.models import IntegrationAnalytics
        
        if not self.integration.is_connected:
            return {'success': False, 'error': 'Integration not connected'}
        
        # Set default date range (last 30 days)
        if not end_date:
            end_date = timezone.now().date()
        if not start_date:
            start_date = (timezone.now() - timedelta(days=30)).date()
        
        # Refresh token if needed
        if self.should_refresh_token():
            try:
                self.refresh_access_token()
            except Exception as e:
                return {'success': False, 'error': f'Token refresh failed: {str(e)}'}
        
        # Fetch analytics from platform
        try:
            analytics_data = self.fetch_analytics(start_date, end_date)
        except Exception as e:
            return {'success': False, 'error': f'Failed to fetch analytics: {str(e)}'}
        
        # Store analytics in database
        synced_count = 0
        for date_str, metrics in analytics_data.items():
            try:
                analytics_obj, created = IntegrationAnalytics.objects.update_or_create(
                    integration=self.integration,
                    date=date_str,
                    defaults=metrics
                )
                synced_count += 1
            except Exception as e:
                print(f"Error storing analytics for {date_str}: {e}")
        
        # Update integration sync status
        self.integration.last_sync = timezone.now()
        self.integration.sync_status = 'success'
        self.integration.sync_error = ''
        self.integration.save(update_fields=['last_sync', 'sync_status', 'sync_error'])
        
        return {
            'success': True,
            'synced_count': synced_count,
            'date_range': f'{start_date} to {end_date}'
        }
    
    def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get a summary of analytics data for the last N days.
        Returns aggregated metrics.
        """
        from campaigns.models import IntegrationAnalytics
        from django.db.models import Sum, Avg
        
        since = timezone.now().date() - timedelta(days=days)
        
        analytics_qs = IntegrationAnalytics.objects.filter(
            integration=self.integration,
            date__gte=since
        )
        
        summary = analytics_qs.aggregate(
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks'),
            total_engagement=Sum('engagement'),
            total_reach=Sum('reach'),
            total_conversions=Sum('conversions'),
            total_leads=Sum('leads'),
            total_spend=Sum('spend'),
            total_revenue=Sum('revenue'),
            total_video_views=Sum('video_views'),
            avg_roi=Avg('roi'),
            avg_roas=Avg('roas')
        )
        
        # Convert Decimal to float for JSON serialization
        return {
            'impressions': summary['total_impressions'] or 0,
            'clicks': summary['total_clicks'] or 0,
            'engagement': summary['total_engagement'] or 0,
            'reach': summary['total_reach'] or 0,
            'conversions': summary['total_conversions'] or 0,
            'leads': summary['total_leads'] or 0,
            'spend': float(summary['total_spend'] or 0),
            'revenue': float(summary['total_revenue'] or 0),
            'video_views': summary['total_video_views'] or 0,
            'avg_roi': float(summary['avg_roi'] or 0),
            'avg_roas': float(summary['avg_roas'] or 0),
            'days': days
        }
