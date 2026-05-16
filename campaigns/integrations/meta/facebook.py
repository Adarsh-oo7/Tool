from typing import Dict, Any
from datetime import datetime
from django.conf import settings
from campaigns.integrations.services.base import BaseIntegrationService
import requests


class FacebookAdsService(BaseIntegrationService):
    """
    Facebook Ads integration service.
    Provides read-only access to Facebook Ads performance data.
    """
    
    def __init__(self, integration):
        super().__init__(integration)
        self.api_base = 'https://graph.facebook.com/v19.0'
    
    def connect(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Connect to Facebook Ads using OAuth.
        """
        from campaigns.integrations.services.oauth import OAuthService
        
        oauth = OAuthService(
            client_id=getattr(settings, 'FACEBOOK_APP_ID', ''),
            client_secret=getattr(settings, 'FACEBOOK_APP_SECRET', ''),
            redirect_uri=redirect_uri
        )
        
        token_data = oauth.exchange_code_for_token(
            token_endpoint='https://graph.facebook.com/v19.0/oauth/access_token',
            auth_code=auth_code
        )
        
        # Fetch account info
        account_info = self._fetch_account_info(token_data['access_token'])
        
        return {
            **token_data,
            'account_name': account_info.get('name', 'Facebook Ads'),
            'account_id': account_info.get('id', '')
        }
    
    def refresh_access_token(self) -> str:
        """
        Refresh Facebook Ads access token.
        """
        from campaigns.integrations.services.oauth import OAuthService
        
        refresh_token = self.integration.get_refresh_token()
        if not refresh_token:
            raise ValueError('No refresh token available')
        
        oauth = OAuthService(
            client_id=getattr(settings, 'FACEBOOK_APP_ID', ''),
            client_secret=getattr(settings, 'FACEBOOK_APP_SECRET', ''),
            redirect_uri=getattr(settings, 'FACEBOOK_REDIRECT_URI', '')
        )
        
        token_data = oauth.refresh_token(
            token_endpoint='https://graph.facebook.com/v19.0/oauth/access_token',
            refresh_token=refresh_token
        )
        
        # Update integration with new token
        self.integration.set_access_token(token_data['access_token'])
        if token_data.get('refresh_token'):
            self.integration.set_refresh_token(token_data['refresh_token'])
        self.integration.token_expiry = token_data.get('token_expiry')
        self.integration.save()
        
        return token_data['access_token']
    
    def fetch_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch ad performance data from Facebook Ads.
        """
        access_token = self.integration.get_access_token()
        ad_account_id = self.integration.account_id
        
        if not ad_account_id:
            raise ValueError('Ad Account ID not configured')
        
        # Format dates for Facebook API
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Build insights query
        params = {
            'access_token': access_token,
            'fields': 'impressions,clicks,engagement_rate,spend,conversions,reach',
            'time_range': f'{"since": "{start_date_str}", "until": "{end_date_str}"}',
            'breakdowns': 'date',
            'level': 'account'
        }
        
        response = requests.get(
            f'{self.api_base}/{ad_account_id}/insights',
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response into daily metrics
        analytics_by_date = {}
        
        if 'data' in data:
            for row in data['data']:
                date_str = row.get('date_start', '')
                
                spend = float(row.get('spend', 0))
                conversions = int(row.get('conversions', 0))
                
                # Calculate ROI and ROAS (assuming average conversion value)
                avg_conversion_value = getattr(settings, 'FACEBOOK_AVG_CONVERSION_VALUE', 1000)
                revenue = conversions * avg_conversion_value
                
                roi = (revenue / spend * 100) if spend > 0 else 0
                roas = (revenue / spend) if spend > 0 else 0
                
                analytics_by_date[date_str] = {
                    'impressions': int(row.get('impressions', 0)),
                    'clicks': int(row.get('clicks', 0)),
                    'engagement': int(row.get('engagement_rate', 0) * row.get('impressions', 0) / 100),
                    'reach': int(row.get('reach', 0)),
                    'conversions': conversions,
                    'leads': conversions,
                    'spend': spend,
                    'revenue': revenue,
                    'video_views': 0,
                    'roi': roi,
                    'roas': roas,
                    'raw_data': row
                }
        
        return analytics_by_date
    
    def validate_connection(self) -> bool:
        """
        Validate Facebook Ads connection.
        """
        try:
            access_token = self.integration.get_access_token()
            ad_account_id = self.integration.account_id
            
            if not access_token or not ad_account_id:
                return False
            
            params = {'access_token': access_token}
            response = requests.get(
                f'{self.api_base}/{ad_account_id}',
                params=params
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def _fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch Facebook Ads account information.
        """
        params = {'access_token': access_token}
        
        # List ad accounts
        response = requests.get(
            f'{self.api_base}/me/adaccounts',
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                return data['data'][0]
        
        return {}
