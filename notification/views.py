from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework_simplejwt.tokens import RefreshToken


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # For creating system notifications (admin only)
        if not request.user.is_superuser:
            return Response({'error': 'Only admins can create notifications'},
                          status=status.HTTP_403_FORBIDDEN)
        
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            notification = serializer.save(recipient=request.user)
            return Response(NotificationSerializer(notification).data,
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_notification(self, pk, user):
        notification = get_object_or_404(Notification, pk=pk)
        if notification.recipient != user:
            return None
        return notification
    
    def get(self, request, pk):
        notification = self.get_notification(pk, request.user)
        if not notification:
            return Response({'error': 'Notification not found'},
                          status=status.HTTP_404_NOT_FOUND)
        
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)
    
    def delete(self, request, pk):
        notification = self.get_notification(pk, request.user)
        if not notification:
            return Response({'error': 'Notification not found'},
                          status=status.HTTP_404_NOT_FOUND)
        
        notification.delete()
        return Response({'message': 'Notification deleted'},
                       status=status.HTTP_204_NO_CONTENT)


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Marked as read'})


class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'})


class UnreadNotificationCountView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread_count': count})
    