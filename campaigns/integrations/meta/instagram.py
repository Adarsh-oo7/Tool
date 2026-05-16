from typing import Dict, Any
from datetime import datetime
from django.conf import settings
from campaigns.integrations.services.base import BaseIntegrationService
import requests


class InstagramInsightsService(BaseIntegrationService):
    """
    Instagram Insights integration service.
    Provides read-only access to Instagram business account analytics.
    """
    
    def __init__(self, integration):
        super().__init__(integration)
        self.api_base = 'https://graph.facebook.com/v19.0'
    
    def connect(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Connect to Instagram using Facebook OAuth (Instagram uses Facebook's OAuth).
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
        
        # Fetch Instagram business account info
        account_info = self._fetch_account_info(token_data['access_token'])
        
        return {
            **token_data,
            'account_name': account_info.get('name', 'Instagram Business'),
            'account_id': account_info.get('id', '')
        }
    
    def refresh_access_token(self) -> str:
        """
        Refresh Instagram access token (uses Facebook's token refresh).
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
        Fetch Instagram insights data.
        """
        access_token = self.integration.get_access_token()
        instagram_business_id = self.integration.account_id
        
        if not instagram_business_id:
            raise ValueError('Instagram Business ID not configured')
        
        # Format dates for Instagram API
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Build insights query
        params = {
            'access_token': access_token,
            'metric': 'impressions,reach,engagement,profile_views,website_clicks',
            'period': 'day',
            'since': start_date_str,
            'until': end_date_str
        }
        
        response = requests.get(
            f'{self.api_base}/{instagram_business_id}/insights',
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response into daily metrics
        analytics_by_date = {}
        
        if 'data' in data:
            for metric_data in data['data']:
                metric_name = metric_data.get('name', '')
                values = metric_data.get('values', [])
                
                for value_entry in values:
                    date_str = value_entry.get('end_time', '').split('T')[0]
                    
                    if date_str not in analytics_by_date:
                        analytics_by_date[date_str] = {
                            'impressions': 0,
                            'clicks': 0,
                            'engagement': 0,
                            'reach': 0,
                            'conversions': 0,
                            'leads': 0,
                            'spend': 0,
                            'revenue': 0,
                            'video_views': 0,
                            'roi': 0,
                            'roas': 0,
                            'raw_data': {}
                        }
                    
                    value = value_entry.get('value', 0)
                    
                    if metric_name == 'impressions':
                        analytics_by_date[date_str]['impressions'] = int(value)
                    elif metric_name == 'reach':
                        analytics_by_date[date_str]['reach'] = int(value)
                    elif metric_name == 'engagement':
                        analytics_by_date[date_str]['engagement'] = int(value)
                    elif metric_name == 'profile_views':
                        analytics_by_date[date_str]['clicks'] = int(value)
                    elif metric_name == 'website_clicks':
                        analytics_by_date[date_str]['clicks'] += int(value)
        
        return analytics_by_date
    
    def validate_connection(self) -> bool:
        """
        Validate Instagram connection.
        """
        try:
            access_token = self.integration.get_access_token()
            instagram_business_id = self.integration.account_id
            
            if not access_token or not instagram_business_id:
                return False
            
            params = {'access_token': access_token}
            response = requests.get(
                f'{self.api_base}/{instagram_business_id}',
                params=params
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def _fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch Instagram business account information.
        """
        params = {'access_token': access_token}
        
        # Get user's Instagram business accounts
        response = requests.get(
            f'{self.api_base}/me/accounts',
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                # Get Instagram business account from the page
                page_id = data['data'][0]['id']
                response = requests.get(
                    f'{self.api_base}/{page_id}?fields=instagram_business_account',
                    params=params
                )
                if response.status_code == 200:
                    ig_data = response.json()
                    if ig_data.get('instagram_business_account'):
                        ig_id = ig_data['instagram_business_account']['id']
                        response = requests.get(
                            f'{self.api_base}/{ig_id}',
                            params=params
                        )
                        if response.status_code == 200:
                            return response.json()
        
        return {}
