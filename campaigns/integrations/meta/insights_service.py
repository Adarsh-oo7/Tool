import requests
from typing import Dict, Any
from datetime import datetime

class MetaInsightsService:
    """
    Service for fetching analytics from Facebook Pages and Instagram Business accounts.
    """
    
    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def get_facebook_page_insights(self, page_id: str) -> Dict[str, Any]:
        """Fetch core metrics for a Facebook Page."""
        metrics = [
            'page_impressions',
            'page_engagements',
            'page_post_engagements',
            'page_fan_adds' # New Likes
        ]
        url = f"{self.BASE_URL}/{page_id}/insights"
        params = {
            'metric': ','.join(metrics),
            'period': 'day',
            'access_token': self.access_token
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_instagram_insights(self, instagram_id: str) -> Dict[str, Any]:
        """Fetch core metrics for an Instagram Business Account."""
        metrics = [
            'impressions',
            'reach',
            'profile_views',
            'follower_count'
        ]
        url = f"{self.BASE_URL}/{instagram_id}/insights"
        params = {
            'metric': ','.join(metrics),
            'period': 'day',
            'access_token': self.access_token
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
