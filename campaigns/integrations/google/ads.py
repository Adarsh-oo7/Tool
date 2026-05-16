from typing import Dict, Any
from datetime import datetime
from django.conf import settings
from campaigns.integrations.services.base import BaseIntegrationService
import requests


class GoogleAdsService(BaseIntegrationService):
    """
    Google Ads integration service.
    Provides read-only access to ad performance data.
    """
    
    def __init__(self, integration):
        super().__init__(integration)
        self.api_base = 'https://googleads.googleapis.com/v17'
    
    def connect(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Connect to Google Ads using OAuth.
        """
        from campaigns.integrations.services.oauth import OAuthService
        
        oauth = OAuthService(
            client_id=getattr(settings, 'GOOGLE_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GOOGLE_CLIENT_SECRET', ''),
            redirect_uri=redirect_uri
        )
        
        token_data = oauth.exchange_code_for_token(
            token_endpoint='https://oauth2.googleapis.com/token',
            auth_code=auth_code
        )
        
        # Fetch account info
        account_info = self._fetch_account_info(token_data['access_token'])
        
        return {
            **token_data,
            'account_name': account_info.get('name', 'Google Ads'),
            'account_id': account_info.get('id', '')
        }
    
    def refresh_access_token(self) -> str:
        """
        Refresh Google Ads access token.
        """
        from campaigns.integrations.services.oauth import OAuthService
        
        refresh_token = self.integration.get_refresh_token()
        if not refresh_token:
            raise ValueError('No refresh token available')
        
        oauth = OAuthService(
            client_id=getattr(settings, 'GOOGLE_CLIENT_ID', ''),
            client_secret=getattr(settings, 'GOOGLE_CLIENT_SECRET', ''),
            redirect_uri=getattr(settings, 'GOOGLE_REDIRECT_URI', '')
        )
        
        token_data = oauth.refresh_token(
            token_endpoint='https://oauth2.googleapis.com/token',
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
        Fetch ad performance data from Google Ads.
        """
        access_token = self.integration.get_access_token()
        customer_id = self.integration.account_id
        
        if not customer_id:
            raise ValueError('Customer ID not configured')
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'developer-token': getattr(settings, 'GOOGLE_ADS_DEVELOPER_TOKEN', '')
        }
        
        # Format dates for Google Ads API
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Build report query
        query = f'''
            SELECT
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.engagements,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE segments.date BETWEEN '{start_date_str}' AND '{end_date_str}'
        '''
        
        body = {
            'query': query
        }
        
        response = requests.post(
            f'{self.api_base}/customers/{customer_id}/googleAds:searchStream',
            headers=headers,
            json=body
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response into daily metrics
        analytics_by_date = {}
        
        for row in data:
            date_str = row.get('segments', {}).get('date', '')
            metrics = row.get('metrics', {})
            
            # Convert micros to regular currency
            spend = float(metrics.get('cost_micros', 0)) / 1_000_000
            revenue = float(metrics.get('conversions_value', 0))
            
            # Calculate ROI and ROAS
            roi = (revenue / spend * 100) if spend > 0 else 0
            roas = (revenue / spend) if spend > 0 else 0
            
            analytics_by_date[date_str] = {
                'impressions': int(metrics.get('impressions', 0)),
                'clicks': int(metrics.get('clicks', 0)),
                'engagement': int(metrics.get('engagements', 0)),
                'reach': 0,  # Google Ads doesn't provide reach directly
                'conversions': int(metrics.get('conversions', 0)),
                'leads': int(metrics.get('conversions', 0)),  # Assuming conversions = leads
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
        Validate Google Ads connection.
        """
        try:
            access_token = self.integration.get_access_token()
            customer_id = self.integration.account_id
            
            if not access_token or not customer_id:
                return False
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'developer-token': getattr(settings, 'GOOGLE_ADS_DEVELOPER_TOKEN', '')
            }
            
            response = requests.get(
                f'{self.api_base}/customers/{customer_id}/campaigns',
                headers=headers
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def _fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch Google Ads account information.
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'developer-token': getattr(settings, 'GOOGLE_ADS_DEVELOPER_TOKEN', '')
        }
        
        # List accessible customers
        response = requests.get(
            f'{self.api_base}/customers:listAccessibleCustomers',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('resourceNames'):
                # Get the first customer's details
                customer_id = data['resourceNames'][0].split('/')[-1]
                response = requests.get(
                    f'{self.api_base}/customers/{customer_id}',
                    headers=headers
                )
                if response.status_code == 200:
                    return response.json()
        
        return {}
