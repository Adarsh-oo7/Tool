from typing import Dict, Any
from datetime import datetime
from django.conf import settings
from campaigns.integrations.services.base import BaseIntegrationService
import requests


class YouTubeAnalyticsService(BaseIntegrationService):
    """
    YouTube Analytics integration service.
    Provides read-only access to YouTube channel analytics.
    """
    
    def __init__(self, integration):
        super().__init__(integration)
        self.api_base = 'https://youtubeanalytics.googleapis.com/v2'
    
    def connect(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Connect to YouTube Analytics using Google OAuth.
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
        
        # Fetch channel info
        account_info = self._fetch_account_info(token_data['access_token'])
        
        return {
            **token_data,
            'account_name': account_info.get('channelTitle', 'YouTube Channel'),
            'account_id': account_info.get('id', '')
        }
    
    def refresh_access_token(self) -> str:
        """
        Refresh YouTube Analytics access token.
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
        Fetch YouTube analytics data.
        """
        access_token = self.integration.get_access_token()
        channel_id = self.integration.account_id
        
        if not channel_id:
            raise ValueError('Channel ID not configured')
        
        # Format dates for YouTube API
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Build report request
        body = {
            'ids': f'channel=={channel_id}',
            'startDate': start_date_str,
            'endDate': end_date_str,
            'metrics': 'views,estimatedMinutesWatched,subscribersGained,likes,comments',
            'dimensions': 'day',
            'sort': 'day'
        }
        
        response = requests.post(
            f'{self.api_base}/reports',
            headers=headers,
            json=body
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response into daily metrics
        analytics_by_date = {}
        
        if 'rows' in data:
            for row in data['rows']:
                date_str = row[0]  # First column is date
                
                analytics_by_date[date_str] = {
                    'impressions': 0,  # YouTube doesn't provide impressions in basic reports
                    'clicks': int(row[3] or 0) + int(row[4] or 0),  # likes + comments as engagement
                    'engagement': int(row[3] or 0) + int(row[4] or 0),
                    'reach': int(row[0] or 0),  # Use views as reach
                    'conversions': 0,
                    'leads': 0,
                    'spend': 0,
                    'revenue': 0,
                    'video_views': int(row[1] or 0),
                    'roi': 0,
                    'roas': 0,
                    'raw_data': row
                }
        
        return analytics_by_date
    
    def validate_connection(self) -> bool:
        """
        Validate YouTube Analytics connection.
        """
        try:
            access_token = self.integration.get_access_token()
            channel_id = self.integration.account_id
            
            if not access_token or not channel_id:
                return False
            
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f'https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}',
                headers=headers
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def _fetch_account_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch YouTube channel information.
        """
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get user's channels
        response = requests.get(
            'https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('items'):
                return data['items'][0]['snippet']
        
        return {}
