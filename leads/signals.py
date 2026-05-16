from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

# We use apps.get_model to avoid circular imports
def get_customer_model():
    return apps.get_model('leads', 'Customer')

@receiver(post_save, sender='calls.CallLog')
def update_customer_timeline_call(sender, instance, created, **kwargs):
    if created and instance.lead and instance.lead.customer:
        customer = instance.lead.customer
        customer.add_timeline_event('call', {
            'outcome': instance.outcome,
            'notes': instance.notes,
            'staff': instance.staff.full_name if instance.staff else 'System',
            'duration': instance.duration_seconds
        })
        customer.update_interaction_stats('call')

@receiver(post_save, sender='field_visits.FieldVisit')
def update_customer_timeline_visit(sender, instance, created, **kwargs):
    if created and instance.lead and instance.lead.customer:
        customer = instance.lead.customer
        customer.add_timeline_event('visit_started', {
            'staff': instance.staff.full_name if instance.staff else 'System',
            'branch': instance.branch.name if instance.branch else 'N/A'
        })
        customer.update_interaction_stats('visit')

@receiver(post_save, sender='field_visits.VisitReport')
def update_customer_timeline_visit_report(sender, instance, created, **kwargs):
    if created and instance.visit.lead and instance.visit.lead.customer:
        customer = instance.visit.lead.customer
        customer.add_timeline_event('visit_completed', {
            'outcome': instance.outcome,
            'notes': instance.notes,
            'time_spent': instance.time_spent_minutes
        })

@receiver(post_save, sender='leads.FollowUp')
def update_customer_timeline_followup(sender, instance, created, **kwargs):
    if created and instance.lead and instance.lead.customer:
        customer = instance.lead.customer
        customer.add_timeline_event('followup_scheduled', {
            'date': instance.scheduled_date.isoformat() if instance.scheduled_date else None,
            'note': instance.note,
        })
    elif instance.completed and instance.lead and instance.lead.customer:
        customer = instance.lead.customer
        customer.add_timeline_event('followup_completed', {
            'note': instance.note,
            'completed_at': instance.completed_at.isoformat() if instance.completed_at else None
        })
