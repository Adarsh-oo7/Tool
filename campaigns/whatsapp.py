"""
WhatsApp Business API service for Bindu Jewellery.

Development mode: real HTTP calls to Meta Graph API.
All sends are logged. Errors stored in CampaignLead.error.
Retries handled at Celery task level — not here.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger('whatsapp')


class WhatsAppError(Exception):
    """Raised when Meta API returns a non-2xx response."""
    def __init__(self, message: str, status_code: int = 0, response_body: dict = None):
        super().__init__(message)
        self.status_code   = status_code
        self.response_body = response_body or {}

    def __str__(self):
        return f'WhatsAppError [{self.status_code}]: {super().__str__()}'


class WhatsAppService:
    """
    Thin wrapper around the Meta WhatsApp Cloud API (Graph API v19.0).
    Reads config from settings:
        WHATSAPP_PHONE_NUMBER_ID
        WHATSAPP_ACCESS_TOKEN
        WHATSAPP_API_VERSION  (default: v19.0)
    """

    def __init__(self):
        self.phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
        self.access_token    = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
        self.api_version     = getattr(settings, 'WHATSAPP_API_VERSION', 'v19.0')
        self.base_url        = f'https://graph.facebook.com/{self.api_version}'

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type':  'application/json',
        }

    def _endpoint(self) -> str:
        return f'{self.base_url}/{self.phone_number_id}/messages'

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Ensure phone has country code — default +91 (India)."""
        phone = phone.strip().replace(' ', '').replace('-', '')
        if not phone.startswith('+'):
            phone = '+91' + phone
        return phone

    def _post(self, payload: dict) -> dict:
        endpoint = self._endpoint()
        logger.info(f'[WhatsApp] POST {endpoint} payload={payload}')
        try:
            resp = requests.post(endpoint, json=payload, headers=self._headers(), timeout=10)
        except requests.RequestException as e:
            raise WhatsAppError(str(e))

        logger.info(f'[WhatsApp] response status={resp.status_code} body={resp.text[:300]}')

        if not resp.ok:
            try:
                body = resp.json()
            except Exception:
                body = {'raw': resp.text}
            raise WhatsAppError(
                body.get('error', {}).get('message', 'Unknown error'),
                status_code=resp.status_code,
                response_body=body,
            )
        return resp.json()

    # ── Public API ─────────────────────────────────────────────────────────────

    def send_text(self, phone: str, message: str) -> dict:
        """Send a plain-text WhatsApp message."""
        payload = {
            'messaging_product': 'whatsapp',
            'to':   self._normalize_phone(phone),
            'type': 'text',
            'text': {'body': message},
        }
        return self._post(payload)

    def send_template(self, phone: str, template_name: str, params: list[str]) -> dict:
        """
        Send a pre-approved Meta template message.
        params: list of body parameter strings, e.g. ['Adarsh', 'Trivandrum']
        """
        payload = {
            'messaging_product': 'whatsapp',
            'to':   self._normalize_phone(phone),
            'type': 'template',
            'template': {
                'name':     template_name,
                'language': {'code': 'en_IN'},
                'components': [
                    {
                        'type':       'body',
                        'parameters': [{'type': 'text', 'text': p} for p in params],
                    }
                ] if params else [],
            },
        }
        return self._post(payload)

    def send_media(self, phone: str, media_url: str, caption: str = '') -> dict:
        """Send an image URL with optional caption."""
        payload = {
            'messaging_product': 'whatsapp',
            'to':   self._normalize_phone(phone),
            'type': 'image',
            'image': {
                'link':    media_url,
                'caption': caption,
            },
        }
        return self._post(payload)
