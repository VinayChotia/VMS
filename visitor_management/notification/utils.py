from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification

def send_notification(recipient, notification_type, title, message, data=None):
    """Send notification to a specific user"""
    if data is None:
        data = {}
    
    # Save to database
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        data=data
    )
    
    # Send via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{recipient.id}',
        {
            'type': 'send_notification',
            'data': {
                'id': notification.id,
                'type': notification_type,
                'title': title,
                'message': message,
                'data': data,
                'created_at': notification.created_at.isoformat()
            }
        }
    )
    
    return notification

def send_approval_request_notification(approver, visitor):
    """Send notification to approver about new visitor approval request"""
    send_notification(
        recipient=approver,
        notification_type='approval_request',
        title='New Visitor Approval Request',
        message=f'{visitor.created_by.full_name} has requested approval for visitor {visitor.full_name}',
        data={
            'visitor_id': visitor.id,
            'visitor_name': visitor.full_name,
            'requested_by': visitor.created_by.full_name
        }
    )

def send_approval_response_notification(visitor, approver, status):
    """Send notification to visitor creator about approval response"""
    send_notification(
        recipient=visitor.created_by,
        notification_type='approval_response',
        title=f'Visitor Request {status.capitalize()}',
        message=f'{approver.full_name} has {status} the visitor request for {visitor.full_name}',
        data={
            'visitor_id': visitor.id,
            'visitor_name': visitor.full_name,
            'approver': approver.full_name,
            'status': status
        }
    )