from rest_framework import serializers
from .models import Company, Branch, Segment


class SegmentSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)

    class Meta:
        model  = Segment
        fields = ['id', 'branch', 'name', 'name_display', 'description', 'is_active']
        read_only_fields = ['id']


class BranchSerializer(serializers.ModelSerializer):
    segments = SegmentSerializer(many=True, read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model  = Branch
        fields = [
            'id', 'company', 'company_name', 'name', 'address',
            'phone', 'lat', 'lng', 'is_active', 'created_at', 'segments',
        ]
        read_only_fields = ['id', 'created_at']


class BranchListSerializer(serializers.ModelSerializer):
    """Lightweight version for dropdowns / foreign key choices."""
    class Meta:
        model  = Branch
        fields = ['id', 'name', 'is_active']


class CompanySerializer(serializers.ModelSerializer):
    branches = BranchListSerializer(many=True, read_only=True)

    class Meta:
        model  = Company
        fields = ['id', 'name', 'logo', 'address', 'phone', 'email', 'created_at', 'branches']
        read_only_fields = ['id', 'created_at']
