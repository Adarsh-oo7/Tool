from rest_framework import serializers
from .models import Sale


class SaleSerializer(serializers.ModelSerializer):
    staff_name    = serializers.CharField(source='staff.full_name', read_only=True)
    branch_name   = serializers.CharField(source='branch.name', read_only=True)
    segment_name  = serializers.CharField(source='segment.get_name_display', read_only=True)
    lead_name     = serializers.CharField(source='lead.name', read_only=True)

    class Meta:
        model  = Sale
        fields = [
            'id', 'lead', 'lead_name', 'branch', 'branch_name',
            'segment', 'segment_name', 'staff', 'staff_name',
            'campaign', 'product_name', 'product_detail',
            'amount', 'weight_grams', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'staff', 'branch']  # ← add branch