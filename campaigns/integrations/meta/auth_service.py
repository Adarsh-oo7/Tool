from django.conf import settings
import requests
from typing import Dict, Any, List
from ..services.base import BaseIntegrationService

class MetaAuthService:
    """
    Handles Meta OAuth flow and token management.
    Supports Facebook, Instagram, and WhatsApp.
    """
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    @staticmethod
    def get_auth_url(redirect_uri: str, state: str = "") -> str:
        """Generate Meta OAuth URL."""
        scopes = [
            'public_profile',
            'email',
            'pages_show_list',
            'pages_read_engagement'
        ]
        scope_str = ','.join(scopes)
        return (
            f"https://www.facebook.com/v18.0/dialog/oauth?"
            f"client_id={settings.META_APP_ID}&"
            f"redirect_uri={redirect_uri}&"
            f"scope={scope_str}&"
            f"state={state}"
        )

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange auth code for a short-lived user access token."""
        url = f"{self.BASE_URL}/oauth/access_token"
        params = {
            'client_id': settings.META_APP_ID,
            'client_secret': settings.META_APP_SECRET,
            'redirect_uri': redirect_uri,
            'code': code
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_long_lived_token(self, short_lived_token: str) -> str:
        """Exchange short-lived token for a 60-day long-lived token."""
        url = f"{self.BASE_URL}/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': settings.META_APP_ID,
            'client_secret': settings.META_APP_SECRET,
            'fb_exchange_token': short_lived_token
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('access_token')

    def get_pages(self, user_access_token: str) -> List[Dict[str, Any]]:
        """Fetch all Facebook pages managed by the user."""
        url = f"{self.BASE_URL}/me/accounts"
        params = {'access_token': user_access_token}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('data', [])
