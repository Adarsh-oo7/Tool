from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Notification
from .serializers import NotificationSerializer


from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationViewSet(viewsets.ModelViewSet):
    """Users read their own notifications. Admins can create new ones."""
    permission_classes = [IsAuthenticated]
    serializer_class   = NotificationSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['is_read', 'notif_type']
    ordering           = ['-created_at']
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def perform_create(self, serializer):
        # Base creation for a single recipient or broadcast
        is_broadcast = self.request.data.get('is_broadcast') == 'true' or self.request.data.get('is_broadcast') is True
        
        if is_broadcast:
            # Create notifications for all active users
            active_users = User.objects.filter(is_active=True)
            for user in active_users:
                # We skip the sender if needed, but usually admin wants to see it too
                Notification.objects.create(
                    recipient=user,
                    sender=self.request.user,
                    notif_type=self.request.data.get('notif_type', 'announcement'),
                    title=self.request.data.get('title'),
                    body=self.request.data.get('body'),
                    image=self.request.FILES.get('image'),
                    is_broadcast=True
                )
        else:
            serializer.save(sender=self.request.user)

    @action(detail=True, methods=['patch'], url_path='read')
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        return Response({'detail': 'Notification marked as read.'})

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'detail': 'All notifications marked as read.'})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
