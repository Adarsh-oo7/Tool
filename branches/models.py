from django.db import models


class Company(models.Model):
    name       = models.CharField(max_length=200)
    logo       = models.ImageField(upload_to='company/', null=True, blank=True)
    address    = models.TextField(blank=True)
    phone      = models.CharField(max_length=15, blank=True)
    email      = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name


class Branch(models.Model):
    company   = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name      = models.CharField(max_length=100)
    address   = models.TextField()
    phone     = models.CharField(max_length=15, blank=True)
    lat       = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    lng       = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Branches'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} — {self.company.name}'


class Segment(models.Model):
    SEGMENT_CHOICES = [
        ('bridal',     'Bridal Jewellery'),
        ('daily_wear', 'Daily Wear'),
        ('investment', 'Investment Gold'),
        ('diamond',    'Diamond Collection'),
    ]
    branch      = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='segments')
    name        = models.CharField(max_length=20, choices=SEGMENT_CHOICES)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        unique_together = ['branch', 'name']

    def __str__(self):
        return f'{self.get_name_display()} @ {self.branch.name}'