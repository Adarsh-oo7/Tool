from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from core.mixins import BranchScopedMixin
from core.permissions import IsManager, IsOwner
from .models import Task
from .serializers import TaskSerializer

class TaskViewSet(BranchScopedMixin, viewsets.ModelViewSet):
    """
    Tasks assigned to staff.
    Owner/Manager can see and manage all tasks in branch.
    Staff can see tasks assigned to them.
    """
    serializer_class   = TaskSerializer
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['assigned_to', 'status', 'priority', 'branch', 'lead']
    search_fields      = ['title', 'description']
    ordering_fields    = ['due_date', 'created_at', 'priority']

    def get_queryset(self):
        user = self.request.user
        qs   = Task.objects.all().select_related('assigned_to', 'created_by', 'branch', 'lead')
        
        if user.role == 'owner':
            return qs
        
        if user.role == 'manager':
            return qs.filter(branch=user.branch)
            
        # Staff see tasks assigned to them
        return qs.filter(assigned_to=user)

    def perform_create(self, serializer):
        # Auto-set creator and branch
        user = self.request.user
        branch = user.branch if user.branch else serializer.validated_data.get('branch')
        
        if not branch:
            assigned_to = serializer.validated_data.get('assigned_to')
            if assigned_to and assigned_to.branch:
                branch = assigned_to.branch

        serializer.save(created_by=user, branch=branch)
