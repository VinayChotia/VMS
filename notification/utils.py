from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from django.utils import timezone

def send_websocket_notification(user_id, notification_type, data):
    """Send real-time WebSocket notification to a specific user"""
    channel_layer = get_channel_layer()
    group_name = f'user_{user_id}'
    
    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'send_notification',
                'data': {
                    'type': notification_type,
                    'data': data,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
        print(f"WebSocket sent to user {user_id} via {group_name}")
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")

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
    send_websocket_notification(
        recipient.id,
        notification_type,
        {
            'id': notification.id,
            'type': notification_type,
            'title': title,
            'message': message,
            'data': data,
            'created_at': notification.created_at.isoformat()
        }
    )
    
    return notification

def send_approval_request_notification(approver, visitor, sections=None):
    """Send notification to approver about new visitor approval request"""
    
    sections_data = []
    sections_text = ""
    if sections:
        sections_data = [{'id': s.id, 'name': s.name} for s in sections]
        sections_text = f" for sections: {', '.join([s.name for s in sections])}"
    
    message = f'{visitor.created_by.full_name} has requested approval for visitor {visitor.full_name}{sections_text}'
    title = f'New Visitor Approval Request - {len(sections) if sections else 0} Section(s)'
    
    send_notification(
        recipient=approver,
        notification_type='approval_request',
        title=title,
        message=message,
        data={
            'visitor_id': visitor.id,
            'visitor_name': visitor.full_name,
            'requested_by': visitor.created_by.full_name,
            'sections': sections_data,
            'total_sections': len(sections) if sections else 0
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

def send_section_approval_notification(visitor, approver, section, status, other_approver=None, has_consensus=False):
    """Send notification about section approval/rejection with consensus info"""
    
    total_approvers = visitor.selected_approvers.count()
    
    if status == 'approved':
        if has_consensus and total_approvers == 2:
            title = f'CONSENSUS REACHED - {section.name} Access Granted'
            message = f'BOTH approvers have approved {section.name}. The visitor can now access this section.'
            notification_type = 'consensus_reached'
        elif total_approvers == 2:
            title = f'Section Approved - {section.name} (Waiting for other approver)'
            message = f'{approver.full_name} approved {section.name}. Waiting for {other_approver.full_name if other_approver else "other approver"} to also approve for access to be granted.'
            notification_type = 'section_approved'
        else:
            title = f'Section Approved - {section.name}'
            message = f'{approver.full_name} approved {section.name}.'
            notification_type = 'section_approved'
    else:
        title = f'Section Rejected - {section.name}'
        message = f'{approver.full_name} rejected access to {section.name}.'
        notification_type = 'section_rejected'
    
    notification_data = {
        'visitor_id': visitor.id,
        'visitor_name': visitor.full_name,
        'section_id': section.id,
        'section_name': section.name,
        'status': status,
        'approver_id': approver.id,
        'approver_name': approver.full_name,
        'has_consensus': has_consensus,
        'total_approvers': total_approvers
    }
    
    # Notify creator via WebSocket and Database
    send_notification(
        recipient=visitor.created_by,
        notification_type=notification_type,
        title=title,
        message=message,
        data=notification_data
    )
    
    # Notify the other approver if applicable
    if other_approver and total_approvers == 2 and status == 'approved' and not has_consensus:
        send_notification(
            recipient=other_approver,
            notification_type='approval_update',
            title=f'Counter-approval Needed - {section.name}',
            message=f'{approver.full_name} approved {section.name}. Your approval is now needed to grant access.',
            data={
                'visitor_id': visitor.id,
                'visitor_name': visitor.full_name,
                'section_id': section.id,
                'section_name': section.name,
                'other_approver_name': approver.full_name
            }
        )
    
    # If consensus reached, also notify the other approver (they already got the consensus notification via the creator notification? No, send separately)
    if has_consensus and total_approvers == 2 and other_approver:
        send_notification(
            recipient=other_approver,
            notification_type='consensus_reached',
            title=f'CONSENSUS REACHED - {section.name} Access Granted',
            message=f'BOTH approvers have approved {section.name}. The visitor can now access this section.',
            data=notification_data
        )

def send_visitor_status_change_notification(recipient, visitor, old_status, new_status, progress=None):
    """Send notification when visitor overall status changes"""
    
    if new_status == 'approved':
        title = 'Visitor Fully Approved'
        message = f'{visitor.full_name} has been fully approved by all approvers and can now check in.'
        notification_type = 'status_change'
    elif new_status == 'rejected':
        title = '✗ Visitor Rejected'
        message = f'{visitor.full_name}\'s visit request has been rejected.'
        notification_type = 'status_change'
    elif new_status == 'partially_approved':
        title = 'Visitor Partially Approved'
        accessible = progress.get('sections_accessible', 0) if progress else 0
        message = f'{visitor.full_name} has {accessible} section(s) with consensus approval.'
        notification_type = 'status_change'
    else:
        title = 'Visitor Status Updated'
        message = f'{visitor.full_name}\'s status changed from {old_status} to {new_status}.'
        notification_type = 'status_change'
    
    send_notification(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        data={
            'visitor_id': visitor.id,
            'visitor_name': visitor.full_name,
            'old_status': old_status,
            'new_status': new_status,
            'progress': progress if progress else {}
        }
    )