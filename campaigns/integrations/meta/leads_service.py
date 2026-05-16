import requests
from typing import List, Dict, Any
from django.utils import timezone
from leads.models import Lead, Customer
from branches.models import Branch

class MetaLeadsService:
    """
    Service for retrieving leads from Meta Lead Gen Forms.
    """
    
    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, page_access_token: str):
        self.access_token = page_access_token

    def fetch_form_leads(self, form_id: str) -> List[Dict[str, Any]]:
        """Fetch leads for a specific Meta Lead Form."""
        url = f"{self.BASE_URL}/{form_id}/leads"
        params = {
            'access_token': self.access_token,
            'fields': 'id,created_time,field_data,ad_id,ad_name,form_id'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('data', [])

    def process_lead(self, meta_lead: Dict[str, Any], branch: Branch, platform: str = 'facebook'):
        """
        Process a raw Meta lead and save it to the internal CRM.
        Maps Meta field_data to internal Lead model.
        """
        field_data = {item['name']: item['values'][0] for item in meta_lead.get('field_data', [])}
        
        email = field_data.get('email')
        phone = field_data.get('phone_number') or field_data.get('phone')
        name = field_data.get('full_name') or f"{field_data.get('first_name', '')} {field_data.get('last_name', '')}".strip()

        if not phone:
            return None # Cannot process lead without phone

        # 1. Ensure Customer exists or create one
        customer, _ = Customer.objects.get_or_create(
            phone=phone,
            defaults={'name': name or 'Meta Lead', 'email': email}
        )

        # 2. Create the Lead record
        lead = Lead.objects.create(
            customer=customer,
            name=name or 'Meta Lead',
            phone=phone,
            email=email,
            source=platform,
            branch=branch,
            notes=f"Meta Form Lead: {meta_lead.get('ad_name', 'Unknown Ad')}",
            stage='new'
        )
        
        return lead
