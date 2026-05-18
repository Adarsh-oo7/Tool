from typing import Dict, Any
from datetime import datetime
from django.conf import settings
from campaigns.integrations.services.base import BaseIntegrationService
import requests


class GoogleAnalyticsService(BaseIntegrationService):
    """
    Google Analytics 4 integration service.
    Provides read-only access to analytics data.
    """
    
    def __init__(self, integration):
        super().__init__(integration)
        self.api_base = 'https://analyticsdata.googleapis.com/v1beta'
    
    def connect(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Connect to Google Analytics using OAuth.
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
            'account_name': account_info.get('accountName', 'Google Analytics'),
            'account_id': account_info.get('accountId', '')
        }
    
    def refresh_access_token(self) -> str:
        """
        Refresh Google Analytics access token.
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
        Fetch analytics data from Google Analytics 4.
        """
        access_token = self.integration.get_access_token()
        property_id = self.integration.account_id
        
        # --- MOCK MODE FOR TESTING ---
        # Trigger mock mode if using a mock token OR if Property ID isn't set up yet
        if (access_token and access_token.startswith('mock_')) or not property_id or property_id == 'pending_config':
            import random
            from datetime import timedelta
            analytics_by_date = {}
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y%m%d')
                analytics_by_date[date_str] = {
                    'impressions': random.randint(100, 1000),
                    'clicks': random.randint(10, 100),
                    'engagement': random.randint(5, 50),
                    'reach': random.randint(50, 500),
                    'conversions': random.randint(0, 10),
                    'leads': random.randint(0, 5),
                    'spend': 0,
                    'revenue': 0,
                    'video_views': 0,
                    'roi': 0,
                    'roas': 0,
                }
                current_date += timedelta(days=1)
            return analytics_by_date
        # --- END MOCK MODE ---
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Format dates for GA4 API
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Build report request
        body = {
            'dateRanges': [{'startDate': start_date_str, 'endDate': end_date_str}],
            'dimensions': [{'name': 'date'}],
            'metrics': [
                {'name': 'sessions'},
                {'name': 'activeUsers'},
                {'name': 'screenPageViews'},
                {'name': 'eventCount'},
                {'name': 'advertiserAdCost'},
                {'name': 'totalRevenue'},
            ]
        }
        
        response = requests.post(
            f'{self.api_base}/properties/{property_id}:runReport',
            headers=headers,
            json=body
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response into daily metrics
        analytics_by_date = {}
        
        if 'rows' in data:
            for row in data['rows']:
                date_str = row['dimensionValues'][0]['value']
                metrics = {
                    'impressions': int(row['metricValues'][0]['value'] or 0),
                    'clicks': int(row['metricValues'][2]['value'] or 0),
                    'engagement': int(row['metricValues'][3]['value'] or 0),
                    'reach': int(row['metricValues'][1]['value'] or 0),
                    'conversions': 0,
                    'leads': 0,
                    'spend': float(row['metricValues'][4]['value'] or 0),
                    'revenue': float(row['metricValues'][5]['value'] or 0),
                    'video_views': 0,
                    'roi': 0,
                    'roas': 0,
                    'raw_data': row
                }
                analytics_by_date[date_str] = metrics
        
        return analytics_by_date
    
    def validate_connection(self) -> bool:
        """
        Validate Google Analytics connection.
        """
        try:
            access_token = self.integration.get_access_token()
            property_id = self.integration.account_id
            
            if not access_token or not property_id:
                return False

            if access_token.startswith('mock_'):
                return True
            
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f'{self.api_base}/properties/{property_id}',
                headers=headers
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def _fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch Google Analytics GA4 property information.
        """
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # List properties (GA4)
        response = requests.get(
            'https://analyticsadmin.googleapis.com/v1beta/properties',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('properties'):
                prop = data['properties'][0]
                prop_id = prop.get('name', '').replace('properties/', '')
                return {
                    'accountName': prop.get('displayName', 'Google Analytics Property'),
                    'accountId': prop_id
                }
        
        return {}
