from django.db import models
from django.conf import settings


class Sale(models.Model):
    lead     = models.ForeignKey('leads.Lead', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='sales')
    branch   = models.ForeignKey('branches.Branch', on_delete=models.CASCADE, related_name='sales')
    segment  = models.ForeignKey('branches.Segment', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='sales')
    staff    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, related_name='sales')
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='sales')

    product_name  = models.CharField(max_length=200)
    product_detail= models.TextField(blank=True)
    amount        = models.DecimalField(max_digits=12, decimal_places=2)
    weight_grams  = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [models.Index(fields=['branch', 'created_at'])]

    def __str__(self):
        return f'Sale ₹{self.amount} — {self.product_name} @ {self.branch}'