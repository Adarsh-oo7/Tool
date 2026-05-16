from celery import shared_task
from django.utils import timezone
from django.db.models import Q
import logging

from .models import LocationTrigger, NearbyCustomerAlert
from campaigns.whatsapp import WhatsAppService, WhatsAppError

logger = logging.getLogger('marketing')


@shared_task(bind=True, max_retries=3, name='marketing.tasks.process_location_triggers')
def process_location_triggers(self):
    """Process pending location triggers and send messages"""
    now = timezone.now()
    processed_count = 0
    failed_count = 0
    
    # Get triggers scheduled for now or past
    pending_triggers = LocationTrigger.objects.filter(
        status='pending',
        scheduled_send_time__lte=now
    ).select_related('lead', 'campaign', 'geofence')
    
    service = WhatsAppService()
    
    for trigger in pending_triggers:
        try:
            # Check if campaign is still active
            if not trigger.campaign.is_active_now():
                trigger.status = 'cancelled'
                trigger.save(update_fields=['status'])
                continue
            
            # Send WhatsApp message
            if trigger.lead.phone:
                service.send_text(trigger.lead.phone, trigger.campaign.message)
                
                # Update trigger
                trigger.status = 'sent'
                trigger.sent_at = now
                trigger.save(update_fields=['status', 'sent_at'])
                
                # Create nearby customer alert
                NearbyCustomerAlert.objects.update_or_create(
                    lead=trigger.lead,
                    branch=trigger.geofence.branch,
                    defaults={
                        'distance_meters': 0,  # Customer is in geofence
                        'message_sent': True,
                        'sent_at': now,
                        'campaign_used': trigger.campaign
                    }
                )
                
                processed_count += 1
                logger.info(f'[marketing] Sent location-based message to {trigger.lead.name}')
            
        except WhatsAppError as e:
            trigger.status = 'failed'
            trigger.error_message = str(e)
            trigger.save(update_fields=['status', 'error_message'])
            failed_count += 1
            logger.error(f'[marketing] WhatsApp error for {trigger.lead.name}: {e}')
        
        except Exception as e:
            trigger.status = 'failed'
            trigger.error_message = str(e)
            trigger.save(update_fields=['status', 'error_message'])
            failed_count += 1
            logger.error(f'[marketing] Error processing trigger for {trigger.lead.name}: {e}')
    
    logger.info(f'[marketing] Processed {processed_count} location triggers, {failed_count} failed')
    return {'processed': processed_count, 'failed': failed_count}


@shared_task(bind=True, max_retries=3, name='marketing.tasks.cleanup_old_location_data')
def cleanup_old_location_data(self):
    """Clean up old location data and triggers"""
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    # Clean up old customer locations
    from .models import CustomerLocation
    deleted_locations = CustomerLocation.objects.filter(
        timestamp__lt=cutoff_date
    ).delete()[0]
    
    # Clean up old completed triggers
    deleted_triggers = LocationTrigger.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['sent', 'failed', 'cancelled']
    ).delete()[0]
    
    logger.info(f'[marketing] Cleaned up {deleted_locations} old locations and {deleted_triggers} old triggers')
    return {'deleted_locations': deleted_locations, 'deleted_triggers': deleted_triggers}


@shared_task(bind=True, max_retries=3, name='marketing.tasks.update_proximity_targets')
def update_proximity_targets(self):
    """Update proximity targets for all active leads"""
    from leads.models import Lead
    from branches.models import Branch
    from .models import CustomerLocation, ProximityTarget
    
    updated_count = 0
    
    # Get all active leads with recent locations
    recent_cutoff = timezone.now() - timezone.timedelta(hours=24)
    recent_locations = CustomerLocation.objects.filter(
        timestamp__gte=recent_cutoff
    ).select_related('lead')
    
    for location in recent_locations:
        lead = location.lead
        
        # Check proximity to all branches
        branches = Branch.objects.all()
        
        for branch in branches:
            if branch.lat and branch.lng:
                distance = _calculate_distance(
                    float(location.lat), float(location.lng),
                    float(branch.lat), float(branch.lng)
                )
                
                # Update or create proximity target if within 5km
                if distance <= 5000:
                    proximity_target, created = ProximityTarget.objects.update_or_create(
                        branch=branch,
                        lead=lead,
                        defaults={'distance_meters': distance}
                    )
                    
                    if not created:
                        proximity_target.distance_meters = distance
                        proximity_target.save(update_fields=['distance_meters'])
                    
                    updated_count += 1
    
    logger.info(f'[marketing] Updated {updated_count} proximity targets')
    return {'updated_count': updated_count}


def _calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points in meters"""
    import math
    
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


@shared_task(bind=True, max_retries=3, name='marketing.tasks.send_nearby_promotions')
def send_nearby_promotions(self):
    """Send promotional messages to customers near branches"""
    from leads.models import Lead
    from branches.models import Branch
    from .models import CustomerLocation, NearbyCustomerAlert
    from campaigns.whatsapp import WhatsAppService, WhatsAppError
    
    now = timezone.now()
    sent_count = 0
    
    # Get nearby alerts that haven't been sent
    nearby_alerts = NearbyCustomerAlert.objects.filter(
        message_sent=False,
        distance_meters__lte=100  # Within 100m
    ).select_related('lead', 'branch')
    
    service = WhatsAppService()
    
    for alert in nearby_alerts:
        try:
            if alert.lead.phone:
                # Create personalized promotion message
                message = (
                    f"🎉 You're very close to {alert.branch.name}! "
                    f"Visit today for a special discount on our latest collection. "
                    f"We're just {int(alert.distance_meters)} meters away! "
                    f"Address: {alert.branch.address}"
                )
                
                service.send_text(alert.lead.phone, message)
                
                # Update alert
                alert.message_sent = True
                alert.sent_at = now
                alert.save(update_fields=['message_sent', 'sent_at'])
                
                sent_count += 1
                logger.info(f'[marketing] Sent nearby promotion to {alert.lead.name}')
        
        except WhatsAppError as e:
            logger.error(f'[marketing] WhatsApp error for nearby promotion to {alert.lead.name}: {e}')
        except Exception as e:
            logger.error(f'[marketing] Error sending nearby promotion to {alert.lead.name}: {e}')
    
    logger.info(f'[marketing] Sent {sent_count} nearby promotions')
    return {'sent_count': sent_count}
