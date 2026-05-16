from ..services.base import BaseIntegrationService
from .auth_service import MetaAuthService
from .insights_service import MetaInsightsService
from .leads_service import MetaLeadsService
from typing import Dict, Any
from datetime import datetime

class FacebookAdsService(BaseIntegrationService):
    """
    Unified Meta Service for Facebook Ads and Page Insights.
    """
    
    def connect(self, auth_code: str, redirect_uri: str) -> Dict[str, Any]:
        auth = MetaAuthService()
        token_data = auth.exchange_code_for_token(auth_code, redirect_uri)
        long_token = auth.get_long_lived_token(token_data['access_token'])
        
        # In a real scenario, we would then fetch the list of pages
        # and let the user select which page to connect.
        # For now, we store the long-lived user token.
        self.integration.set_access_token(long_token)
        self.integration.is_connected = True
        self.integration.save()
        
        return {
            'access_token': long_token,
            'platform': 'facebook_ads'
        }

    def refresh_access_token(self) -> str:
        # Meta long-lived tokens last 60 days and don't refresh the same way as Google.
        # Usually, you re-authenticate or use a specific refresh endpoint.
        return self.integration.get_access_token()

    def fetch_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Fetch Page Insights from Meta and normalize into unified format."""
        insights = MetaInsightsService(self.integration.get_access_token())
        page_id = self.integration.metadata.get('page_id')
        
        if not page_id:
            return {}

        raw_data = insights.get_facebook_page_insights(page_id)
        
        # Parse Meta's nested JSON response for Facebook
        analytics_by_date = {}
        for metric in raw_data.get('data', []):
            name = metric['name']
            for value_obj in metric.get('values', []):
                date_str = value_obj['end_time'].split('T')[0]
                val = value_obj['value']
                
                if date_str not in analytics_by_date:
                    analytics_by_date[date_str] = {
                        'impressions': 0, 'clicks': 0, 'engagement': 0, 
                        'reach': 0, 'conversions': 0, 'leads': 0, 
                        'spend': 0, 'revenue': 0
                    }
                
                if name == 'page_impressions':
                    analytics_by_date[date_str]['impressions'] = val
                elif name == 'page_engagements':
                    analytics_by_date[date_str]['engagement'] = val
                elif name == 'page_fan_adds':
                    analytics_by_date[date_str]['conversions'] = val
        
        # Trigger Lead Sync if there are configured forms
        self.sync_leads()
        
        return analytics_by_date

    def sync_leads(self):
        """Fetch and process leads from all active forms."""
        metadata = self.integration.metadata
        form_ids = metadata.get('form_ids', [])
        
        if not form_ids:
            return
            
        leads_service = MetaLeadsService(self.integration.get_access_token())
        for form_id in form_ids:
            try:
                raw_leads = leads_service.fetch_form_leads(form_id)
                for raw_lead in raw_leads:
                    leads_service.process_lead(raw_lead, self.integration.branch)
            except Exception as e:
                print(f"Error syncing leads for form {form_id}: {e}")

    def validate_connection(self) -> bool:
        return self.integration.is_connected and bool(self.integration.access_token)
