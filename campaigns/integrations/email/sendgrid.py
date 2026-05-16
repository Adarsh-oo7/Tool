from typing import Dict, Any
from datetime import datetime
from django.conf import settings
from campaigns.integrations.services.base import BaseIntegrationService
import requests


class SendGridService(BaseIntegrationService):
    """
    SendGrid integration service.
    Provides read-only access to email campaign analytics.
    """
    
    def __init__(self, integration):
        super().__init__(integration)
        self.api_base = 'https://api.sendgrid.com/v3'
    
    def connect(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Connect to SendGrid using API key.
        Note: SendGrid uses API key, not OAuth for most use cases.
        """
        api_key = auth_code  # Using auth_code as API key for SendGrid
        
        # Fetch account info
        account_info = self._fetch_account_info(api_key)
        
        return {
            'access_token': api_key,
            'refresh_token': None,
            'token_expiry': None,
            'account_name': account_info.get('username', 'SendGrid'),
            'account_id': account_info.get('user_id', '')
        }
    
    def refresh_access_token(self) -> str:
        """
        SendGrid doesn't use refresh tokens (API key based).
        """
        return self.integration.get_access_token()
    
    def fetch_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch email campaign analytics from SendGrid.
        """
        api_key = self.integration.get_access_token()
        
        if not api_key:
            raise ValueError('API key not configured')
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Format dates for SendGrid API
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Fetch campaigns
        response = requests.get(
            f'{self.api_base}/campaigns',
            headers=headers,
            params={'limit': 100}
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response into daily metrics
        analytics_by_date = {}
        
        if 'result' in data:
            for campaign in data['result']:
                # Get campaign statistics
                stats_response = requests.get(
                    f'{self.api_base}/campaigns/{campaign["id"]}/stats',
                    headers=headers,
                    params={'start_date': start_date_str, 'end_date': end_date_str}
                )
                
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    
                    # Use created_at as date
                    created_at = campaign.get('created_at', '')
                    if created_at:
                        date_str = created_at.split('T')[0]
                        
                        opens = stats.get('opens', 0)
                        clicks = stats.get('clicks', 0)
                        delivered = stats.get('delivered', 0)
                        
                        analytics_by_date[date_str] = {
                            'impressions': delivered,
                            'clicks': clicks,
                            'engagement': opens,
                            'reach': opens,
                            'conversions': 0,
                            'leads': 0,
                            'spend': 0,
                            'revenue': 0,
                            'video_views': 0,
                            'roi': 0,
                            'roas': 0,
                            'raw_data': stats
                        }
        
        return analytics_by_date
    
    def validate_connection(self) -> bool:
        """
        Validate SendGrid connection.
        """
        try:
            api_key = self.integration.get_access_token()
            
            if not api_key:
                return False
            
            headers = {'Authorization': f'Bearer {api_key}'}
            response = requests.get(
                f'{self.api_base}/user/profile',
                headers=headers
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def _fetch_account_info(self, api_key: str) -> Dict[str, Any]:
        """
        Fetch SendGrid account information.
        """
        headers = {'Authorization': f'Bearer {api_key}'}
        
        response = requests.get(
            f'{self.api_base}/user/profile',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        
        return {}
