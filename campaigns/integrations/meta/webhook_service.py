import hmac
import hashlib
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from .leads_service import MetaLeadsService
from ...models import Integration

class MetaWebhookService:
    """
    Handles incoming Meta Webhooks for Lead Gen and Messaging.
    """

    @staticmethod
    def verify_signature(payload: bytes, signature: str) -> bool:
        """Verify that the webhook request came from Meta."""
        if not signature:
            return False
        
        expected_sig = hmac.new(
            settings.META_APP_SECRET.encode(),
            payload,
            hashlib.sha1
        ).hexdigest()
        
        return hmac.compare_digest(f"sha1={expected_sig}", signature)

    def handle_lead_webhook(self, data: dict):
        """Process incoming lead notification."""
        # Meta sends a 'leadgen' entry with a lead_id.
        # We then use the LeadsService to fetch the full lead details.
        entries = data.get('entry', [])
        for entry in entries:
            changes = entry.get('changes', [])
            for change in changes:
                if change.get('field') == 'leadgen':
                    lead_id = change['value']['leadgen_id']
                    page_id = change['value']['page_id']
                    
                    # 1. Find the integration record for this Page ID
                    try:
                        integration = Integration.objects.get(
                            platform='facebook_ads',
                            metadata__page_id=page_id
                        )
                        
                        # 2. Fetch the lead details using the stored token
                        service = MetaLeadsService(integration.get_access_token())
                        meta_lead = service.fetch_form_leads(lead_id) # Should be fetch_single_lead
                        
                        # 3. Process and save to CRM
                        service.process_lead(meta_lead[0], integration.branch)
                        
                    except Integration.DoesNotExist:
                        continue # Page not connected to our system
        
        return True
