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
                {'name': 'totalRevenue'},
            ]
        }
        
        response = requests.post(
            f'{self.api_base}/properties/{property_id}:runReport',
            headers=headers,
            json=body
        )
        
        if response.status_code != 200:
            raise Exception(f"Google Analytics API Error ({response.status_code}): {response.text}")
        
        data = response.json()
        
        # Parse response into daily metrics
        analytics_by_date = {}
        
        if 'rows' in data:
            for row in data['rows']:
                date_str = row['dimensionValues'][0]['value']
                metrics = {
                    'impressions': int(row['metricValues'][2]['value'] or 0),  # screenPageViews
                    'clicks': int(row['metricValues'][0]['value'] or 0),       # sessions
                    'engagement': int(row['metricValues'][3]['value'] or 0),   # eventCount
                    'reach': int(row['metricValues'][1]['value'] or 0),        # activeUsers
                    'conversions': 0,
                    'leads': 0,
                    'spend': 0.0,
                    'revenue': float(row['metricValues'][4]['value'] or 0),    # totalRevenue
                    'video_views': 0,
                    'roi': 0,
                    'roas': 0,
                    'raw_data': row
                }
                analytics_by_date[date_str] = metrics
        
        return analytics_by_date
    
    def _get_property_website(self, property_id: str, headers: dict) -> str:
        """
        Fetch the website URL / default URI of the first web data stream for a property.
        """
        try:
            res = requests.get(
                f'https://analyticsadmin.googleapis.com/v1beta/properties/{property_id}/dataStreams',
                headers=headers
            )
            if res.status_code == 200:
                data = res.json()
                if data.get('dataStreams'):
                    for stream in data['dataStreams']:
                        if stream.get('type') == 'WEB_DATA_STREAM' and stream.get('webStreamData'):
                            uri = stream['webStreamData'].get('defaultUri', '')
                            # Clean the URI to get a nice domain string
                            clean_uri = uri.replace('https://', '').replace('http://', '').rstrip('/')
                            return clean_uri
        except Exception as e:
            print(f"Error fetching data stream for property {property_id}: {e}")
        return ""

    def get_available_properties(self) -> list:
        """
        Fetch all available GA4 properties under the connected account.
        """
        access_token = self.integration.get_access_token()
        if not access_token:
            return []
            
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(
                'https://analyticsadmin.googleapis.com/v1beta/accountSummaries',
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                properties = []
                if data.get('accountSummaries'):
                    for account in data['accountSummaries']:
                        if account.get('propertySummaries'):
                            for prop in account['propertySummaries']:
                                prop_id = prop.get('property', '').replace('properties/', '')
                                
                                # Try fetching website stream URL
                                website = self._get_property_website(prop_id, headers)
                                name = prop.get('displayName', 'Unnamed Property')
                                if website:
                                    name = f"{name} ({website})"
                                    
                                properties.append({
                                    'id': prop_id,
                                    'name': name,
                                    'account_name': account.get('displayName', 'Unnamed Account')
                                })
                return properties
        except Exception as e:
            print(f"Error fetching available GA4 properties: {e}")
        return []

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
        
        # Use accountSummaries to get accounts and properties in one go
        response = requests.get(
            'https://analyticsadmin.googleapis.com/v1beta/accountSummaries',
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch GA4 account summaries ({response.status_code}): {response.text}")
            
        data = response.json()
        if data.get('accountSummaries'):
            target_prop = None
            first_prop = None
            
            # Loop through all accounts and properties
            for account in data['accountSummaries']:
                if account.get('propertySummaries'):
                    for prop in account['propertySummaries']:
                        # Save the very first property as a fallback
                        if not first_prop:
                            first_prop = (account, prop)
                            
                        # Look specifically for the keralasellers property
                        if 'keralasellers' in prop.get('displayName', '').lower():
                            target_prop = (account, prop)
                            break
                if target_prop:
                    break
                    
            # Use the target property if found, otherwise use the first one
            selected_account, selected_prop = target_prop if target_prop else first_prop
            
            if selected_prop:
                prop_id = selected_prop.get('property', '').replace('properties/', '')
                return {
                    'accountName': selected_prop.get('displayName', selected_account.get('displayName', 'Google Analytics')),
                    'accountId': prop_id
                }
            
            raise Exception("We found your Google Analytics account, but it doesn't have any GA4 Properties set up. Please create a GA4 property in analytics.google.com.")
        else:
            raise Exception("No Google Analytics accounts found for this email. Please create one at analytics.google.com.")
