from rest_framework import serializers
from .models import Task
from accounts.serializers import StaffListSerializer

class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    created_by_name  = serializers.CharField(source='created_by.full_name', read_only=True)
    branch_name      = serializers.CharField(source='branch.name', read_only=True)
    lead_name        = serializers.CharField(source='lead.name', read_only=True)

    class Meta:
        model  = Task
        fields = [
            'id', 'title', 'description', 'assigned_to', 'assigned_to_name',
            'created_by', 'created_by_name', 'branch', 'branch_name',
            'lead', 'lead_name', 'priority', 'status', 'due_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
        extra_kwargs = {
            'branch': {'required': False}
        }
