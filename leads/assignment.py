"""
Smart Call Assignment Algorithm Service

Implements intelligent lead assignment based on:
1. Load Balancing - Assign to staff with least pending calls
2. Segment Expertise - Match lead segment with staff expertise
3. Geographic Proximity - Field staff assigned to leads in their area
4. Performance-based - Hot leads assigned to top performers
5. Follow-up Continuity - Same staff handles follow-ups
"""

from django.db.models import Count, Q, F
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import math

User = get_user_model()


class AssignmentEngine:
    """Smart lead assignment engine with multiple strategies."""
    
    def __init__(self, lead, branch=None):
        self.lead = lead
        self.branch = branch or lead.branch
        
    def assign(self, strategy='auto'):
        """
        Assign lead using specified strategy.
        
        Strategies:
        - auto: Uses all rules in priority order
        - load_balancing: Only load balancing
        - segment_expertise: Only segment matching
        - geographic: Only geographic proximity
        - performance: Only performance-based
        """
        if strategy == 'auto':
            return self._auto_assign()
        elif strategy == 'load_balancing':
            return self._load_balancing_assign()
        elif strategy == 'segment_expertise':
            return self._segment_expertise_assign()
        elif strategy == 'geographic':
            return self._geographic_assign()
        elif strategy == 'performance':
            return self._performance_assign()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def _auto_assign(self):
        """
        Auto assignment using priority order:
        1. Check if lead has existing assigned staff (follow-up continuity)
        2. Try segment expertise match
        3. Try geographic proximity for field staff
        4. Try performance-based for hot leads
        5. Fall back to load balancing
        """
        # Rule 5: Follow-up Continuity
        if self.lead.assigned_to:
            return self.lead.assigned_to
        
        # Rule 2: Segment Expertise
        if self.lead.segment:
            expert = self._segment_expertise_assign()
            if expert:
                return expert
        
        # Rule 3: Geographic Proximity (for field staff)
        if self.lead.location or (self.lead.customer and self.lead.customer.location):
            field_staff = self._geographic_assign()
            if field_staff:
                return field_staff
        
        # Rule 4: Performance-based (for hot leads)
        if self.lead.is_hot or self.lead.score >= 70:
            top_performer = self._performance_assign()
            if top_performer:
                return top_performer
        
        # Rule 1: Load Balancing (fallback)
        return self._load_balancing_assign()
    
    def _load_balancing_assign(self):
        """
        Rule 1: Load Balancing
        Count pending calls per staff and assign to staff with least pending calls.
        """
        from leads.models import Lead
        
        # Get eligible staff (telecaller, staff, field_staff) in the branch
        eligible_roles = ['staff', 'telecaller', 'field_staff']
        staff_list = User.objects.filter(
            role__in=eligible_roles,
            branch=self.branch,
            is_active=True
        )
        
        if not staff_list.exists():
            return None
        
        # Count pending leads for each staff
        pending_counts = (
            Lead.objects.filter(
                assigned_to__in=staff_list,
                stage__in=['new', 'contacted', 'interested', 'scheduled'],
                branch=self.branch
            )
            .values('assigned_to')
            .annotate(pending_count=Count('id'))
        )
        
        # Create a dict of staff_id -> pending_count
        pending_dict = {item['assigned_to']: item['pending_count'] for item in pending_counts}
        
        # Find staff with minimum pending count
        min_pending = float('inf')
        best_staff = None
        
        for staff in staff_list:
            pending = pending_dict.get(staff.id, 0)
            if pending < min_pending:
                min_pending = pending
                best_staff = staff
        
        return best_staff
    
    def _segment_expertise_assign(self):
        """
        Rule 2: Segment Expertise
        Match lead segment with staff expertise.
        """
        if not self.lead.segment:
            return None
        
        # Get staff who are experts in this segment
        expert_staff = User.objects.filter(
            expert_segments=self.lead.segment,
            branch=self.branch,
            is_active=True,
            role__in=['staff', 'telecaller', 'field_staff']
        ).first()
        
        return expert_staff
    
    def _geographic_assign(self):
        """
        Rule 3: Geographic Proximity
        Assign field staff to leads in their area.
        Uses Haversine formula to calculate distance.
        """
        from leads.models import Lead
        
        # Get lead location
        lead_location = self.lead.location or (self.lead.customer.location if self.lead.customer else None)
        if not lead_location:
            return None
        
        # Get field staff in the branch
        field_staff = User.objects.filter(
            role='field_staff',
            branch=self.branch,
            is_active=True
        )
        
        if not field_staff.exists():
            return None
        
        # For simplicity, use location string matching
        # In production, would use lat/lng coordinates with Haversine
        # Here we check if staff address contains lead location keywords
        location_keywords = lead_location.lower().split()
        
        best_staff = None
        best_match_count = 0
        
        for staff in field_staff:
            if staff.address:
                address_lower = staff.address.lower()
                match_count = sum(1 for keyword in location_keywords if keyword in address_lower)
                if match_count > best_match_count:
                    best_match_count = match_count
                    best_staff = staff
        
        return best_staff if best_match_count > 0 else None
    
    def _performance_assign(self):
        """
        Rule 4: Performance-based Assignment
        Hot leads (score >= 70) assigned to top performers.
        Performance measured by conversion rate in last 30 days.
        """
        from leads.models import Lead
        from sales.models import Sale
        
        # Get eligible staff
        eligible_roles = ['staff', 'telecaller', 'field_staff']
        staff_list = User.objects.filter(
            role__in=eligible_roles,
            branch=self.branch,
            is_active=True
        )
        
        if not staff_list.exists():
            return None
        
        # Calculate performance metrics for each staff
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        performance_scores = []
        
        for staff in staff_list:
            # Count leads assigned in last 30 days
            leads_assigned = Lead.objects.filter(
                assigned_to=staff,
                created_at__gte=thirty_days_ago
            ).count()
            
            # Count leads converted in last 30 days
            leads_converted = Lead.objects.filter(
                assigned_to=staff,
                stage='converted',
                updated_at__gte=thirty_days_ago
            ).count()
            
            # Calculate conversion rate
            conversion_rate = (leads_converted / leads_assigned * 100) if leads_assigned > 0 else 0
            
            # Calculate total sales amount
            total_sales = Sale.objects.filter(
                staff=staff,
                created_at__gte=thirty_days_ago
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            # Overall performance score (conversion rate weighted 60%, sales weighted 40%)
            performance_score = (conversion_rate * 0.6) + (total_sales / 10000 * 0.4)
            
            performance_scores.append({
                'staff': staff,
                'score': performance_score,
                'conversion_rate': conversion_rate,
                'total_sales': total_sales
            })
        
        # Sort by performance score (descending)
        performance_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top performer
        if performance_scores:
            return performance_scores[0]['staff']
        
        return None
    
    @staticmethod
    def auto_assign_lead(lead_id):
        """
        Static method to auto-assign a lead by ID.
        Useful for Celery tasks and signals.
        """
        from leads.models import Lead
        
        try:
            lead = Lead.objects.get(id=lead_id)
            engine = AssignmentEngine(lead)
            assigned_staff = engine.assign(strategy='auto')
            
            if assigned_staff:
                lead.assigned_to = assigned_staff
                lead.save(update_fields=['assigned_to'])
                
                # Add timeline event
                if lead.customer:
                    lead.customer.add_timeline_event('lead_assigned', {
                        'staff': assigned_staff.full_name,
                        'strategy': 'auto'
                    })
                
                return assigned_staff
        except Lead.DoesNotExist:
            return None
        
        return None


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in kilometers.
    """
    from math import radians, cos, sin, asin, sqrt
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r
