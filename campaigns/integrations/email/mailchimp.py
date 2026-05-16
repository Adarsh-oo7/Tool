from typing import Dict, Any
from datetime import datetime
from django.conf import settings
from campaigns.integrations.services.base import BaseIntegrationService
import requests


class MailchimpService(BaseIntegrationService):
    """
    Mailchimp integration service.
    Provides read-only access to email campaign analytics.
    """
    
    def __init__(self, integration):
        super().__init__(integration)
        self.api_base = 'https://usX.api.mailchimp.com/3.0'  # X will be replaced with data center
    
    def connect(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Connect to Mailchimp using API key.
        Note: Mailchimp uses API key, not OAuth for most use cases.
        """
        # Extract data center from API key
        api_key = auth_code  # Using auth_code as API key for Mailchimp
        data_center = api_key.split('-')[-1] if '-' in api_key else 'us1'
        self.api_base = f'https://{data_center}.api.mailchimp.com/3.0'
        
        # Fetch account info
        account_info = self._fetch_account_info(api_key)
        
        return {
            'access_token': api_key,
            'refresh_token': None,
            'token_expiry': None,
            'account_name': account_info.get('name', 'Mailchimp'),
            'account_id': account_info.get('account_id', '')
        }
    
    def refresh_access_token(self) -> str:
        """
        Mailchimp doesn't use refresh tokens (API key based).
        """
        return self.integration.get_access_token()
    
    def fetch_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch email campaign analytics from Mailchimp.
        """
        api_key = self.integration.get_access_token()
        
        if not api_key:
            raise ValueError('API key not configured')
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Fetch campaigns
        response = requests.get(
            f'{self.api_base}/campaigns',
            headers=headers,
            params={'count': 100}
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response into daily metrics
        analytics_by_date = {}
        
        if 'campaigns' in data:
            for campaign in data['campaigns']:
                # Get campaign report
                report_response = requests.get(
                    f'{self.api_base}/reports/{campaign["id"]}',
                    headers=headers
                )
                
                if report_response.status_code == 200:
                    report = report_response.json()
                    
                    # Use send_time as date
                    send_time = campaign.get('send_time', '')
                    if send_time:
                        date_str = send_time.split('T')[0]
                        
                        opens = report.get('opens', {}).get('opens_total', 0)
                        clicks = report.get('clicks', {}).get('clicks_total', 0)
                        emails_sent = report.get('emails_sent', 0)
                        
                        analytics_by_date[date_str] = {
                            'impressions': emails_sent,
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
                            'raw_data': report
                        }
        
        return analytics_by_date
    
    def validate_connection(self) -> bool:
        """
        Validate Mailchimp connection.
        """
        try:
            api_key = self.integration.get_access_token()
            
            if not api_key:
                return False
            
            headers = {'Authorization': f'Bearer {api_key}'}
            response = requests.get(
                f'{self.api_base}/',
                headers=headers
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def _fetch_account_info(self, api_key: str) -> Dict[str, Any]:
        """
        Fetch Mailchimp account information.
        """
        headers = {'Authorization': f'Bearer {api_key}'}
        
        response = requests.get(
            f'{self.api_base}/',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        
        return {}
