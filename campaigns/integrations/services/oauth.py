from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
import requests


class OAuthService:
    """
    Generic OAuth service for handling OAuth flows.
    Can be extended for specific platforms.
    """
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    def get_auth_url(self, auth_endpoint: str, scope: str, state: Optional[str] = None) -> str:
        """
        Generate the OAuth authorization URL.
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': scope,
            'response_type': 'code',
        }
        if state:
            params['state'] = state
        
        import urllib.parse
        return f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
    
    def exchange_code_for_token(
        self,
        token_endpoint: str,
        auth_code: str,
        grant_type: str = 'authorization_code'
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'grant_type': grant_type,
        }
        
        response = requests.post(token_endpoint, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Calculate token expiry
        expires_in = token_data.get('expires_in')
        token_expiry = None
        if expires_in:
            token_expiry = timezone.now() + timedelta(seconds=expires_in)
        
        return {
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'token_expiry': token_expiry,
            'scope': token_data.get('scope'),
            'raw_response': token_data
        }
    
    def refresh_token(
        self,
        token_endpoint: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }
        
        response = requests.post(token_endpoint, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Calculate token expiry
        expires_in = token_data.get('expires_in')
        token_expiry = None
        if expires_in:
            token_expiry = timezone.now() + timedelta(seconds=expires_in)
        
        return {
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token', refresh_token),
            'token_expiry': token_expiry,
            'raw_response': token_data
        }
