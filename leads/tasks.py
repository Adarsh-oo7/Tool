from celery import shared_task
from django.utils import timezone
from django.db.models import Q, Count, F
from django.contrib.auth import get_user_model
from datetime import timedelta
import logging

from .models import Lead, FollowUp, LeadActivity
from campaigns.whatsapp import WhatsAppService, WhatsAppError
from notifications.models import Notification

logger = logging.getLogger('leads')


@shared_task(bind=True, max_retries=3, name='leads.tasks.auto_create_followups')
def auto_create_followups(self):
    """Automatically create follow-ups for new leads and based on lead stages"""
    created_count = 0
    
    # Get leads that need follow-ups
    now = timezone.now()
    
    # 1. New leads (create initial follow-up)
    new_leads = Lead.objects.filter(
        stage='new',
        created_at__gte=now - timedelta(hours=24)
    ).filter(
        ~Q(followups__followup_type='auto')
    )
    
    for lead in new_leads:
        # Schedule first follow-up within 24 hours
        followup_date = lead.created_at + timedelta(hours=24)
        
        followup = FollowUp.objects.create(
            lead=lead,
            followup_type='call',
            priority='high' if lead.is_hot else 'medium',
            scheduled_date=followup_date,
            note=f"Initial follow-up for new lead from {lead.get_source_display()}",
            auto_generated=True,
            created_by=lead.assigned_to or lead.created_by
        )
        
        # Record activity
        LeadActivity.objects.create(
            lead=lead,
            actor=lead.assigned_to or lead.created_by,
            action='auto_followup_created',
            detail=f"Auto-generated initial follow-up scheduled for {followup_date}"
        )
        
        created_count += 1
        logger.info(f'[leads] Auto-follow-up created for new lead: {lead.name}')
    
    # 2. Interested leads (schedule follow-up)
    interested_leads = Lead.objects.filter(
        stage='interested',
        updated_at__gte=now - timedelta(hours=48)
    ).filter(
        ~Q(followups__followup_type='auto', followups__status='pending')
    )
    
    for lead in interested_leads:
        # Schedule follow-up within 3 days
        followup_date = now + timedelta(days=3)
        
        followup = FollowUp.objects.create(
            lead=lead,
            followup_type='whatsapp',
            priority='high',
            scheduled_date=followup_date,
            note=f"Follow-up for interested lead - budget: {lead.budget or 'Not specified'}",
            auto_generated=True,
            created_by=lead.assigned_to or lead.created_by
        )
        
        LeadActivity.objects.create(
            lead=lead,
            actor=lead.assigned_to or lead.created_by,
            action='auto_followup_created',
            detail=f"Auto-generated follow-up for interested lead scheduled for {followup_date}"
        )
        
        created_count += 1
        logger.info(f'[leads] Auto-follow-up created for interested lead: {lead.name}')
    
    # 3. Follow-up after missed calls
    missed_followups = FollowUp.objects.filter(
        followup_type='call',
        status='missed',
        updated_at__gte=now - timedelta(hours=24)
    )
    
    for missed in missed_followups:
        # Schedule retry within 2 days
        retry_date = now + timedelta(days=2)
        
        retry_followup = FollowUp.objects.create(
            lead=missed.lead,
            followup_type='whatsapp',
            priority='medium',
            scheduled_date=retry_date,
            note=f"Retry after missed call on {missed.scheduled_date.date()}",
            auto_generated=True,
            created_by=missed.created_by
        )
        
        LeadActivity.objects.create(
            lead=missed.lead,
            actor=missed.created_by,
            action='auto_followup_created',
            detail=f"Auto-generated retry follow-up after missed call scheduled for {retry_date}"
        )
        
        created_count += 1
        logger.info(f'[leads] Auto retry follow-up created for missed call: {missed.lead.name}')
    
    logger.info(f'[leads] Created {created_count} auto follow-ups')
    return {'created_count': created_count}


@shared_task(bind=True, max_retries=3, name='leads.tasks.send_followup_reminders')
def send_followup_reminders(self):
    """Send reminders for upcoming follow-ups"""
    now = timezone.now()
    reminder_count = 0
    
    # Get follow-ups scheduled for today and tomorrow
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = today_start + timedelta(days=2)
    
    upcoming_followups = FollowUp.objects.filter(
        scheduled_date__gte=today_start,
        scheduled_date__lt=tomorrow_end,
        status='pending',
        reminder_sent=False
    ).select_related('lead', 'created_by')
    
    for followup in upcoming_followups:
        try:
            # Check if follow-up is within reminder window (2 hours before)
            reminder_time = followup.scheduled_date - timedelta(hours=2)
            
            if now >= reminder_time:
                # Create notification for assigned user
                if followup.lead.assigned_to:
                    notification = Notification.objects.create(
                        recipient=followup.lead.assigned_to,
                        title='Follow-up Reminder',
                        message=f'Reminder: {followup.get_followup_type_display()} with {followup.lead.name} scheduled for {followup.scheduled_date.strftime("%I:%M %p")}',
                        notif_type='followup',
                        metadata={
                            'followup_id': followup.id,
                            'lead_id': followup.lead.id,
                            'scheduled_date': followup.scheduled_date.isoformat()
                        }
                    )
                    reminder_count += 1
                
                # Mark reminder as sent
                followup.reminder_sent = True
                followup.save(update_fields=['reminder_sent'])
                
                logger.info(f'[leads] Follow-up reminder sent for: {followup.lead.name}')
        
        except Exception as e:
            logger.error(f'[leads] Error sending follow-up reminder: {e}')
            continue
    
    logger.info(f'[leads] Sent {reminder_count} follow-up reminders')
    return {'reminder_count': reminder_count}


@shared_task(bind=True, max_retries=3, name='leads.tasks.mark_overdue_followups')
def mark_overdue_followups(self):
    """Mark overdue follow-ups and update lead scores"""
    now = timezone.now()
    overdue_count = 0
    
    # Get follow-ups that are overdue
    overdue_followups = FollowUp.objects.filter(
        scheduled_date__lt=now,
        status='pending'
    ).select_related('lead')
    
    for followup in overdue_followups:
        # Mark as missed
        followup.status = 'missed'
        followup.save(update_fields=['status'])
        
        # Update lead score (decrease for missed follow-ups)
        lead = followup.lead
        lead.score = max(0, lead.score - 5)  # Decrease by 5 points
        lead.save(update_fields=['score'])
        
        # Record activity
        LeadActivity.objects.create(
            lead=lead,
            actor=followup.created_by,
            action='followup_missed',
            detail=f"Follow-up missed: {followup.get_followup_type_display()} scheduled for {followup.scheduled_date.date()}"
        )
        
        overdue_count += 1
        logger.info(f'[leads] Follow-up marked as overdue: {lead.name}')
    
    logger.info(f'[leads] Marked {overdue_count} follow-ups as overdue')
    return {'overdue_count': overdue_count}


@shared_task(bind=True, max_retries=3, name='leads.tasks.auto_followup_sequence')
def auto_followup_sequence(self, lead_id, followup_id):
    """Create automatic follow-up sequence based on follow-up outcome"""
    try:
        lead = Lead.objects.get(id=lead_id)
        followup = FollowUp.objects.get(id=followup_id)
        
        # Determine next follow-up based on outcome and lead stage
        next_followup_date = None
        next_followup_type = 'call'
        next_followup_note = ''
        
        if followup.outcome == 'interested':
            # Lead is interested, follow up in 2 days
            next_followup_date = timezone.now() + timedelta(days=2)
            next_followup_type = 'whatsapp'
            next_followup_note = 'Follow-up based on expressed interest'
            lead.stage = 'interested'
            lead.score = min(100, lead.score + 10)  # Increase score
            
        elif followup.outcome == 'not_interested':
            # Lead not interested, follow up in 7 days with different approach
            next_followup_date = timezone.now() + timedelta(days=7)
            next_followup_type = 'email'
            next_followup_note = 'Re-engagement follow-up after initial rejection'
            lead.score = max(0, lead.score - 3)  # Slightly decrease score
            
        elif followup.outcome == 'call_later':
            # Lead asked to call later
            next_followup_date = timezone.now() + timedelta(days=3)
            next_followup_type = 'call'
            next_followup_note = 'Follow-up as requested by lead'
            
        elif followup.outcome == 'scheduled_visit':
            # Visit scheduled, follow up after visit
            next_followup_date = timezone.now() + timedelta(days=1)
            next_followup_type = 'call'
            next_followup_note = 'Post-visit follow-up'
            lead.stage = 'scheduled'
            lead.score = min(100, lead.score + 15)  # Significant increase
        
        # Save lead changes
        lead.save(update_fields=['stage', 'score'])
        
        # Create next follow-up if date is set
        if next_followup_date:
            next_followup = FollowUp.objects.create(
                lead=lead,
                followup_type=next_followup_type,
                priority='high' if lead.is_hot else 'medium',
                scheduled_date=next_followup_date,
                note=next_followup_note,
                auto_generated=True,
                created_by=followup.created_by
            )
            
            LeadActivity.objects.create(
                lead=lead,
                actor=followup.created_by,
                action='auto_followup_created',
                detail=f"Auto-generated follow-up sequence: {next_followup_type} scheduled for {next_followup_date}"
            )
            
            logger.info(f'[leads] Auto follow-up sequence created for {lead.name}: {next_followup_type} on {next_followup_date}')
            return {
                'lead_id': lead_id,
                'next_followup_id': next_followup.id,
                'next_followup_date': next_followup_date
            }
        
        return {'lead_id': lead_id, 'message': 'No next follow-up scheduled'}
    
    except Lead.DoesNotExist:
        logger.error(f'[leads] Lead {lead_id} not found for follow-up sequence')
        return {'error': 'Lead not found'}
    except FollowUp.DoesNotExist:
        logger.error(f'[leads] FollowUp {followup_id} not found for follow-up sequence')
        return {'error': 'FollowUp not found'}
    except Exception as e:
        logger.error(f'[leads] Error in auto follow-up sequence: {e}')
        return {'error': str(e)}


@shared_task(bind=True, max_retries=3, name='leads.tasks.send_whatsapp_followups')
def send_whatsapp_followups(self):
    """Send automated WhatsApp follow-up messages"""
    now = timezone.now()
    sent_count = 0
    
    # Get WhatsApp follow-ups scheduled for now
    whatsapp_followups = FollowUp.objects.filter(
        followup_type='whatsapp',
        status='pending',
        scheduled_date__lte=now,
        scheduled_date__gte=now - timedelta(hours=1)  # Within the last hour
    ).select_related('lead', 'created_by')
    
    service = WhatsAppService()
    
    for followup in whatsapp_followups:
        try:
            lead = followup.lead
            
            if not lead.phone:
                continue
            
            # Generate personalized message
            message = _generate_followup_message(followup, lead)
            
            # Send WhatsApp message
            service.send_text(lead.phone, message)
            
            # Mark follow-up as in progress
            followup.status = 'in_progress'
            followup.save(update_fields=['status'])
            
            # Record activity
            LeadActivity.objects.create(
                lead=lead,
                actor=followup.created_by,
                action='whatsapp_sent',
                detail=f"Auto WhatsApp follow-up sent: {message[:100]}..."
            )
            
            sent_count += 1
            logger.info(f'[leads] WhatsApp follow-up sent to {lead.name}')
        
        except WhatsAppError as e:
            logger.error(f'[leads] WhatsApp error for {followup.lead.name}: {e}')
            followup.status = 'cancelled'
            followup.save(update_fields=['status'])
        
        except Exception as e:
            logger.error(f'[leads] Error sending WhatsApp follow-up: {e}')
            continue
    
    logger.info(f'[leads] Sent {sent_count} WhatsApp follow-ups')
    return {'sent_count': sent_count}


def _generate_followup_message(followup, lead):
    """Generate personalized follow-up message"""
    messages = {
        'new': f"Hi {lead.name}, this is {followup.created_by.full_name if followup.created_by else 'Bindu Jewellery'}. We received your inquiry and wanted to follow up. Are you available to discuss your requirements?",
        'interested': f"Hi {lead.name}, following up on your interest in our jewellery collection. We have some beautiful pieces that match your preferences. Would you like to see them?",
        'scheduled': f"Hi {lead.name}, just a reminder about your scheduled visit. We're looking forward to showing you our collection. Let us know if you need to reschedule.",
        'default': f"Hi {lead.name}, this is {followup.created_by.full_name if followup.created_by else 'Bindu Jewellery'}. Following up on your inquiry. How can we help you today?"
    }
    
    base_message = messages.get(lead.stage, messages['default'])
    
    # Add personalization based on lead data
    if lead.budget:
        base_message += f" We have options within your budget of {lead.budget}."
    
    if lead.product_interest:
        base_message += f" Based on your interest in {lead.product_interest}, we can show you some matching pieces."
    
    if lead.occasion:
        base_message += f" Perfect for {lead.occasion} occasions!"
    
    base_message += f"\n\nCall us at {followup.created_by.phone if followup.created_by and followup.created_by.phone else 'our showroom'} or reply to this message."
    
    return base_message


@shared_task(bind=True, max_retries=3, name='leads.tasks.cleanup_old_followups')
def cleanup_old_followups(self):
    """Clean up old completed/cancelled follow-ups"""
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=90)
    
    deleted_count = FollowUp.objects.filter(
        status__in=['completed', 'cancelled'],
        updated_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f'[leads] Cleaned up {deleted_count} old follow-ups')
    return {'deleted_count': deleted_count}
