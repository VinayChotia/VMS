from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db import models
from .models import CooldownPeriod, Employee, Location, Section, Site, Visitor, VisitorApproval, VisitorSectionApproval, VisitorSectionRequest
from .serializers import (
    CooldownPeriodSerializer, EmployeeSerializer, EmployeeListSerializer, EmployeeRegisterSerializer, LocationSerializer,
    LoginSerializer, SectionSerializer, SiteSerializer, VisitorCheckInSerializer, VisitorCheckOutSerializer, VisitorSerializer, VisitorApprovalResponseSerializer
)
from .permissions import IsEmployee

# Authentication Views
class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = EmployeeRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': EmployeeSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': EmployeeSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Successfully logged out'})
        except Exception:
            return Response({'message': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh = RefreshToken(refresh_token)
            return Response({
                'access': str(refresh.access_token),
            })
        except Exception:
            return Response({'error': 'Invalid refresh token'}, 
                          status=status.HTTP_401_UNAUTHORIZED)


# Employee Views
class EmployeeListView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        employees = Employee.objects.filter(is_available=True)
        serializer = EmployeeListSerializer(employees, many=True)
        return Response(serializer.data)


class CurrentEmployeeView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        serializer = EmployeeSerializer(request.user)
        return Response(serializer.data)


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk, is_available=True)
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data)


# Visitor Views
# needed to be modified after the changes in the architecture including section wise approval requests
# class VisitorListView(APIView):
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def get(self, request):
#         user = request.user
#         if user.is_superuser:
#             visitors = Visitor.objects.all()
#         else:
#             # Employees can see visitors they created or were asked to approve
#             visitors = Visitor.objects.filter(
#                 models.Q(created_by=user) | 
#                 models.Q(selected_approvers=user)
#             ).distinct()
        
#         serializer = VisitorSerializer(visitors, many=True)
#         return Response(serializer.data)
    
#     def post(self, request):
#         serializer = VisitorSerializer(data=request.data)
#         if serializer.is_valid():
#             # Ensure the created_by is set to current user
#             visitor = serializer.save(created_by=request.user)
            
#             # Trigger notifications for approvers
#             from notification.utils import send_approval_request_notification
#             for approver in visitor.selected_approvers.all():
#                 send_approval_request_notification(approver, visitor)
            
#             return Response(VisitorSerializer(visitor).data, 
#                           status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ========== MODIFIED VISITOR CREATION VIEW ==========

class VisitorListView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        user = request.user
        if user.is_superuser:
            visitors = Visitor.objects.all()
        else:
            visitors = Visitor.objects.filter(
                models.Q(created_by=user) | 
                models.Q(selected_approvers=user)
            ).distinct()
        
        serializer = VisitorSerializer(visitors, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """
        Create a new visitor with sections and approvers.
        
        Expected request body:
        {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone_number": "+1234567890",
            "company_name": "ABC Corp",
            "purpose_of_visit": "Meeting",
            "site_id": 1,
            "requested_section_ids": [1, 2, 3, 4],
            "selected_approver_ids": [5, 6],
            "designated_check_in": "2024-01-15T10:00:00Z",
            "designated_check_out": "2024-01-15T17:00:00Z",
            "vehicle_number": "ABC123",
            "id_card_number": "ID123456",
            "host_department": "IT",
            "meeting_room": "Conference Room A"
        }
        """
        data = request.data.copy()
        
        # Validate site
        site_id = data.get('site_id')
        if not site_id:
            return Response({'error': 'site_id is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        site = get_object_or_404(Site, id=site_id, is_active=True)
        
        # Check if site is in cooldown
        if site.is_on_cooldown():
            cooldown = site.get_active_cooldown()
            return Response({
                'error': f'Cannot create visit. {cooldown.get_active_message()}'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Validate requested sections
        requested_section_ids = data.get('requested_section_ids', [])
        if not requested_section_ids:
            return Response({'error': 'At least one section must be requested'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        sections = Section.objects.filter(
            id__in=requested_section_ids, 
            location__site=site, 
            is_active=True
        )
        if sections.count() != len(requested_section_ids):
            return Response({'error': 'One or more sections are invalid or do not belong to the selected site'},
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check section capacities
        for section in sections:
            if not section.is_capacity_available():
                return Response({
                    'error': f'Section "{section.name}" has reached its daily capacity ({section.daily_capacity})'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate approvers (at least 2)
        approver_ids = data.get('selected_approver_ids', [])
        if len(approver_ids) < 2:
            return Response({'error': 'At least 2 approvers are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        approvers = Employee.objects.filter(id__in=approver_ids, is_available=True)
        if approvers.count() != len(approver_ids):
            return Response({'error': 'One or more approvers are invalid'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Remove non-model fields from data
        data.pop('site_id', None)
        data.pop('requested_section_ids', None)
        data.pop('selected_approver_ids', None)
        
        # Create visitor
        visitor_serializer = VisitorSerializer(data=data)
        if visitor_serializer.is_valid():
            with transaction.atomic():
                visitor = visitor_serializer.save(created_by=request.user, site=site)
                
                # Add requested sections
                for section in sections:
                    VisitorSectionRequest.objects.create(
                        visitor=visitor,
                        section=section,
                        requested_by=request.user
                    )
                
                # Add selected approvers
                visitor.selected_approvers.set(approvers)
                
                # Create section approval records for each approver and each section
                for approver in approvers:
                    for section in sections:
                        VisitorSectionApproval.objects.create(
                            visitor=visitor,
                            section=section,
                            approver=approver,
                            status='pending'
                        )
                
                # Create legacy approval records (for backward compatibility)
                for approver in approvers:
                    VisitorApproval.objects.create(
                        visitor=visitor,
                        approver=approver,
                        status='pending'
                    )
                
                # Send notifications
                from notification.utils import send_approval_request_notification
                for approver in approvers:
                    send_approval_request_notification(approver, visitor)
            
            return Response({
                'visitor': VisitorSerializer(visitor).data,
                'requested_sections': [{'id': s.id, 'name': s.name} for s in sections],
                'approvers': [{'id': a.id, 'name': a.full_name} for a in approvers]
            }, status=status.HTTP_201_CREATED)
        
        return Response(visitor_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VisitorDetailView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get_visitor(self, pk, user):
        """Helper method to get visitor with permission check"""
        visitor = get_object_or_404(Visitor, pk=pk)
        
        # Check if user has permission to view this visitor
        if not (user.is_superuser or 
                visitor.created_by == user or 
                visitor.selected_approvers.filter(id=user.id).exists()):
            return None
        return visitor
    
    def get(self, request, pk):
        visitor = self.get_visitor(pk, request.user)
        if not visitor:
            return Response({'error': 'You do not have permission to view this visitor'},
                          status=status.HTTP_403_FORBIDDEN)
        
        serializer = VisitorSerializer(visitor)
        return Response(serializer.data)
    
    def put(self, request, pk):
        visitor = self.get_visitor(pk, request.user)
        if not visitor:
            return Response({'error': 'You do not have permission to edit this visitor'},
                          status=status.HTTP_403_FORBIDDEN)
        
        # Only creator can edit pending visitors
        if visitor.created_by != request.user and visitor.status != 'pending':
            return Response({'error': 'Only the creator can edit pending visitors'},
                          status=status.HTTP_403_FORBIDDEN)
        
        serializer = VisitorSerializer(visitor, data=request.data, partial=True)
        if serializer.is_valid():
            updated_visitor = serializer.save()
            return Response(VisitorSerializer(updated_visitor).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        visitor = self.get_visitor(pk, request.user)
        if not visitor:
            return Response({'error': 'You do not have permission to delete this visitor'},
                          status=status.HTTP_403_FORBIDDEN)
        
        # Only creator can delete pending visitors
        if visitor.created_by != request.user:
            return Response({'error': 'Only the creator can delete this visitor'},
                          status=status.HTTP_403_FORBIDDEN)
        
        visitor.delete()
        return Response({'message': 'Visitor deleted successfully'}, 
                       status=status.HTTP_204_NO_CONTENT)


# class VisitorApproveView(APIView):
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, pk):
#         visitor = get_object_or_404(Visitor, pk=pk)
        
#         # Check if current user is one of the approvers
#         if not visitor.selected_approvers.filter(id=request.user.id).exists():
#             return Response(
#                 {'error': 'You are not authorized to approve this visitor'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Check if already responded
#         approval_record = VisitorApproval.objects.get(
#             visitor=visitor,
#             approver=request.user
#         )
        
#         if approval_record.status != 'pending':
#             return Response(
#                 {'error': f'You have already {approval_record.status} this request'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Update approval
#         serializer = VisitorApprovalResponseSerializer(data=request.data)
#         if serializer.is_valid():
#             status_value = serializer.validated_data['status']
#             comments = serializer.validated_data.get('comments', '')
            
#             with transaction.atomic():
#                 approval_record.status = status_value
#                 approval_record.comments = comments
#                 approval_record.responded_at = timezone.now()
#                 approval_record.save()
                
#                 # Update visitor status
#                 visitor.check_approval_status()
                
#                 # Send notification about approval
#                 from notification.utils import send_approval_response_notification
#                 send_approval_response_notification(visitor, request.user, status_value)
            
#             return Response({
#                 'message': f'Successfully {status_value} the visitor',
#                 'visitor_status': visitor.status
#             })
        
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ========== SECTION-BASED APPROVAL VIEW ==========

class VisitorSectionApprovalView(APIView):
    """
    Approve or reject SPECIFIC SECTIONS for a visitor.
    Each approver can approve only the sections they deem necessary.
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request, visitor_id):
        visitor = get_object_or_404(Visitor, pk=visitor_id)
        
        # Check if current user is an approver for this visitor
        if not visitor.selected_approvers.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not authorized to approve sections for this visitor'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Request body format:
        # {
        #   "section_approvals": [
        #       {"section_id": 1, "status": "approved", "comments": "OK to enter"},
        #       {"section_id": 2, "status": "rejected", "rejection_reason": "No access needed"},
        #       {"section_id": 3, "status": "approved", "comments": "Escort required"}
        #   ]
        # }
        
        section_approvals = request.data.get('section_approvals', [])
        
        if not section_approvals:
            return Response(
                {'error': 'section_approvals list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        
        with transaction.atomic():
            for approval_data in section_approvals:
                section_id = approval_data.get('section_id')
                status_value = approval_data.get('status')
                comments = approval_data.get('comments', '')
                rejection_reason = approval_data.get('rejection_reason', '')
                
                if status_value not in ['approved', 'rejected']:
                    results.append({
                        'section_id': section_id,
                        'status': 'error',
                        'message': 'Status must be approved or rejected'
                    })
                    continue
                
                # Verify section belongs to this visitor's requested sections
                if not visitor.requested_sections.filter(id=section_id).exists():
                    results.append({
                        'section_id': section_id,
                        'status': 'error',
                        'message': 'Section not requested for this visitor'
                    })
                    continue
                
                # Get or create section approval record
                section_approval, created = VisitorSectionApproval.objects.get_or_create(
                    visitor=visitor,
                    section_id=section_id,
                    approver=request.user,
                    defaults={
                        'status': status_value,
                        'comments': comments,
                        'rejection_reason': rejection_reason if status_value == 'rejected' else ''
                    }
                )
                
                if not created and section_approval.status != 'pending':
                    results.append({
                        'section_id': section_id,
                        'section_name': section_approval.section.name,
                        'status': 'skipped',
                        'message': f'Already {section_approval.status} by you'
                    })
                    continue
                
                # Update approval
                section_approval.status = status_value
                section_approval.comments = comments
                
                if status_value == 'rejected':
                    if not rejection_reason:
                        results.append({
                            'section_id': section_id,
                            'status': 'error',
                            'message': 'Rejection reason required'
                        })
                        continue
                    section_approval.rejection_reason = rejection_reason
                else:
                    section_approval.approved_at = timezone.now()
                    section_approval.approved_by = request.user
                
                section_approval.save()
                
                # Send notification for this section approval
                from notification.utils import send_section_approval_notification
                send_section_approval_notification(visitor, request.user, section_approval.section, status_value)
                
                results.append({
                    'section_id': section_id,
                    'section_name': section_approval.section.name,
                    'status': status_value,
                    'message': 'Success'
                })
            
            # Update overall visitor status based on all section approvals
            visitor.check_overall_approval_status()
        
        # Get updated approval summary
        total_sections = visitor.visitor_section_approvals.count()
        approved_count = visitor.visitor_section_approvals.filter(status='approved').count()
        rejected_count = visitor.visitor_section_approvals.filter(status='rejected').count()
        pending_count = total_sections - approved_count - rejected_count
        
        return Response({
            'visitor_id': visitor.id,
            'visitor_status': visitor.status,
            'approval_summary': {
                'total_sections': total_sections,
                'approved': approved_count,
                'rejected': rejected_count,
                'pending': pending_count
            },
            'processed_sections': len(results),
            'results': results
        })


class VisitorPendingSectionsView(APIView):
    """Get all pending sections that need approval from current approver"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, visitor_id):
        visitor = get_object_or_404(Visitor, pk=visitor_id)
        
        # Check if user is approver
        if not visitor.selected_approvers.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not authorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get sections pending for this specific approver
        pending_sections = VisitorSectionApproval.objects.filter(
            visitor=visitor,
            approver=request.user,
            status='pending'
        ).select_related('section', 'section__location', 'section__location__site')
        
        # Get already approved sections
        approved_sections = VisitorSectionApproval.objects.filter(
            visitor=visitor,
            approver=request.user,
            status='approved'
        ).select_related('section')
        
        # Get rejected sections
        rejected_sections = VisitorSectionApproval.objects.filter(
            visitor=visitor,
            approver=request.user,
            status='rejected'
        ).select_related('section')
        
        return Response({
            'visitor': {
                'id': visitor.id,
                'full_name': visitor.full_name,
                'company_name': visitor.company_name,
                'purpose_of_visit': visitor.purpose_of_visit,
                'designated_check_in': visitor.designated_check_in,
                'designated_check_out': visitor.designated_check_out,
                'site': visitor.site.name if visitor.site else None,
            },
            'pending_sections': [
                {
                    'id': sa.section.id,
                    'name': sa.section.name,
                    'location': sa.section.location.name,
                    'site': sa.section.location.site.name,
                    'section_type': sa.section.section_type,
                    'requires_escort': sa.section.requires_escort,
                    'daily_capacity': sa.section.daily_capacity
                }
                for sa in pending_sections
            ],
            'already_approved_sections': [
                {
                    'id': sa.section.id,
                    'name': sa.section.name,
                    'approved_at': sa.approved_at
                }
                for sa in approved_sections
            ],
            'already_rejected_sections': [
                {
                    'id': sa.section.id,
                    'name': sa.section.name,
                    'rejection_reason': sa.rejection_reason
                }
                for sa in rejected_sections
            ],
            'summary': {
                'total_pending': pending_sections.count(),
                'total_approved': approved_sections.count(),
                'total_rejected': rejected_sections.count()
            }
        })

class MyApprovalsView(APIView):
    """View for employee to see all visitors pending their approval"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        pending_approvals = VisitorApproval.objects.filter(
            approver=request.user,
            status='pending'
        ).select_related('visitor')
        
        visitors = [approval.visitor for approval in pending_approvals]
        serializer = VisitorSerializer(visitors, many=True)
        return Response(serializer.data)


class VisitorsByStatusView(APIView):
    """View to filter visitors by status"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, status):
        valid_statuses = ['pending', 'partially_approved', 'approved', 
                         'rejected', 'checked_in', 'checked_out']
        
        if status not in valid_statuses:
            return Response({'error': 'Invalid status'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        if user.is_superuser:
            visitors = Visitor.objects.filter(status=status)
        else:
            visitors = Visitor.objects.filter(
                (models.Q(created_by=user) | models.Q(selected_approvers=user)),
                status=status
            ).distinct()
        
        serializer = VisitorSerializer(visitors, many=True)
        return Response(serializer.data)


class VisitorStatsView(APIView):
    """Get statistics about visitors"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        user = request.user
        
        if user.is_superuser:
            total = Visitor.objects.count()
            pending = Visitor.objects.filter(status='pending').count()
            approved = Visitor.objects.filter(status='approved').count()
            checked_in = Visitor.objects.filter(status='checked_in').count()
            checked_out = Visitor.objects.filter(status='checked_out').count()
            rejected = Visitor.objects.filter(status='rejected').count()
        else:
            total = Visitor.objects.filter(
                models.Q(created_by=user) | models.Q(selected_approvers=user)
            ).distinct().count()
            pending = Visitor.objects.filter(
                models.Q(created_by=user) | models.Q(selected_approvers=user),
                status='pending'
            ).distinct().count()
            approved = Visitor.objects.filter(
                models.Q(created_by=user) | models.Q(selected_approvers=user),
                status='approved'
            ).distinct().count()
            checked_in = Visitor.objects.filter(
                models.Q(created_by=user) | models.Q(selected_approvers=user),
                status='checked_in'
            ).distinct().count()
            checked_out = Visitor.objects.filter(
                models.Q(created_by=user) | models.Q(selected_approvers=user),
                status='checked_out'
            ).distinct().count()
            rejected = Visitor.objects.filter(
                models.Q(created_by=user) | models.Q(selected_approvers=user),
                status='rejected'
            ).distinct().count()
        
        return Response({
            'total': total,
            'pending': pending,
            'approved': approved,
            'checked_in': checked_in,
            'checked_out': checked_out,
            'rejected': rejected
        })


class BulkVisitorApprovalView(APIView):
    """Bulk approve multiple visitors"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request):
        visitor_ids = request.data.get('visitor_ids', [])
        status_value = request.data.get('status')
        comments = request.data.get('comments', '')
        
        if not visitor_ids:
            return Response({'error': 'visitor_ids required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if status_value not in ['approved', 'rejected']:
            return Response({'error': 'Status must be approved or rejected'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        results = []
        for visitor_id in visitor_ids:
            try:
                visitor = Visitor.objects.get(pk=visitor_id)
                
                # Check if user is approver
                if not visitor.selected_approvers.filter(id=request.user.id).exists():
                    results.append({
                        'visitor_id': visitor_id,
                        'status': 'skipped',
                        'message': 'Not authorized'
                    })
                    continue
                
                approval_record = VisitorApproval.objects.get(
                    visitor=visitor,
                    approver=request.user
                )
                
                if approval_record.status != 'pending':
                    results.append({
                        'visitor_id': visitor_id,
                        'status': 'skipped',
                        'message': f'Already {approval_record.status}'
                    })
                    continue
                
                with transaction.atomic():
                    approval_record.status = status_value
                    approval_record.comments = comments
                    approval_record.responded_at = timezone.now()
                    approval_record.save()
                    visitor.check_approval_status()
                    
                    from notification.utils import send_approval_response_notification
                    send_approval_response_notification(visitor, request.user, status_value)
                
                results.append({
                    'visitor_id': visitor_id,
                    'status': status_value,
                    'message': 'Success'
                })
                
            except Visitor.DoesNotExist:
                results.append({
                    'visitor_id': visitor_id,
                    'status': 'error',
                    'message': 'Visitor not found'
                })
        
        return Response({
            'processed': len(results),
            'results': results
        })
    

# class VisitorCheckInView(APIView):
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, pk):
#         visitor = get_object_or_404(Visitor, pk=pk)
        
#         # Check permission
#         if not (request.user.is_superuser or visitor.created_by == request.user):
#             return Response(
#                 {'error': 'You do not have permission to check-in this visitor'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         if visitor.status != 'approved':
#             return Response(
#                 {'error': 'Visitor must be approved before check-in'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         if visitor.actual_check_in:
#             return Response(
#                 {'error': f'Visitor already checked in at {visitor.actual_check_in}'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         serializer = VisitorCheckInSerializer(data=request.data)
#         notes = serializer.initial_data.get('notes') if serializer.is_valid() else None
        
#         try:
#             result = visitor.check_in(notes=notes)
#             return Response({
#                 'message': f'Visitor checked in successfully{result["timing_message"]}',
#                 'check_in_time': result['check_in_time'],
#                 'designated_check_in_time': visitor.designated_check_in,
#                 'early_arrival_minutes': result['early_arrival_minutes'],
#                 'late_arrival_minutes': result['late_arrival_minutes']
#             })
#         except ValueError as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ========== MODIFIED CHECK-IN VIEW ==========

class VisitorCheckInView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request, pk):
        visitor = get_object_or_404(Visitor, pk=pk)
        
        # Check permission
        if not (request.user.is_superuser or visitor.created_by == request.user):
            return Response(
                {'error': 'You do not have permission to check-in this visitor'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # NEW: Check if site is in cooldown
        if visitor.site and visitor.site.is_on_cooldown():
            cooldown = visitor.site.get_active_cooldown()
            return Response(
                {'error': f'Cannot check in. {cooldown.get_active_message()}'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # NEW: Check site daily capacity
        if visitor.site and not visitor.site.is_capacity_available():
            return Response(
                {'error': f'Daily visitor limit reached for {visitor.site.name}. Please try tomorrow.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # NEW: Check if visitor has at least one approved section
        approved_sections_count = visitor.visitor_section_approvals.filter(status='approved').count()
        if approved_sections_count == 0:
            return Response(
                {'error': 'Visitor has no approved sections. Cannot check in.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if visitor.status != 'approved':
            return Response(
                {'error': 'Visitor must be approved before check-in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if visitor.actual_check_in:
            return Response(
                {'error': f'Visitor already checked in at {visitor.actual_check_in}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VisitorCheckInSerializer(data=request.data)
        notes = serializer.initial_data.get('notes') if serializer.is_valid() else None
        
        try:
            result = visitor.check_in(notes=notes)
            
            # Get access matrix for security
            access_matrix = visitor.get_access_matrix()
            
            return Response({
                'message': f'Visitor checked in successfully{result["timing_message"]}',
                'check_in_time': result['check_in_time'],
                'designated_check_in_time': visitor.designated_check_in,
                'early_arrival_minutes': result['early_arrival_minutes'],
                'late_arrival_minutes': result['late_arrival_minutes'],
                'site': visitor.site.name if visitor.site else None,
                'site_capacity_remaining': visitor.site.daily_capacity_limit - visitor.site.get_today_visitor_count() if visitor.site else None,
                'access_matrix': access_matrix,
                'approved_sections_summary': {
                    'total_approved': len([a for a in access_matrix if a['status'] == 'approved']),
                    'requires_escort': [a['section'] for a in access_matrix if a['status'] == 'approved' and a['requires_escort']]
                }
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class VisitorCheckOutView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request, pk):
        visitor = get_object_or_404(Visitor, pk=pk)
        
        # Check permission
        if not (request.user.is_superuser or visitor.created_by == request.user):
            return Response(
                {'error': 'You do not have permission to check-out this visitor'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not visitor.actual_check_in:
            return Response(
                {'error': 'Visitor must check in first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if visitor.actual_check_out:
            return Response(
                {'error': f'Visitor already checked out at {visitor.actual_check_out}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VisitorCheckOutSerializer(data=request.data)
        notes = serializer.initial_data.get('notes') if serializer.is_valid() else None
        
        try:
            result = visitor.check_out(notes=notes)
            response_data = {
                'message': 'Visitor checked out successfully',
                'check_out_time': result['check_out_time'],
                'visit_duration_minutes': result['visit_duration_minutes'],
                'designated_check_out_time': visitor.designated_check_out,
            }
            
            if 'overtime_minutes' in result:
                response_data['message'] = result['message']
                response_data['overtime_minutes'] = result['overtime_minutes']
            
            return Response(response_data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

## Developer Name: Vinay Chotia
## Date : 20-04-2026

# ========== SITE MANAGEMENT VIEWS ==========

class SiteListView(APIView):
    """List all sites - All authenticated employees can view"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        sites = Site.objects.filter(is_active=True)
        serializer = SiteSerializer(sites, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create new site - Superadmin only"""
        if not request.user.is_superuser:
            return Response({'error': 'Only superadmin can create sites'},
                          status=status.HTTP_403_FORBIDDEN)
        
        serializer = SiteSerializer(data=request.data)
        if serializer.is_valid():
            site = serializer.save()
            return Response(SiteSerializer(site).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SiteDetailView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, pk):
        site = get_object_or_404(Site, pk=pk)
        serializer = SiteSerializer(site)
        return Response(serializer.data)
    
    def put(self, request, pk):
        if not request.user.is_superuser:
            return Response({'error': 'Only superadmin can edit sites'},
                          status=status.HTTP_403_FORBIDDEN)
        
        site = get_object_or_404(Site, pk=pk)
        serializer = SiteSerializer(site, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response(SiteSerializer(updated).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response({'error': 'Only superadmin can delete sites'},
                          status=status.HTTP_403_FORBIDDEN)
        
        site = get_object_or_404(Site, pk=pk)
        site.is_active = False  # Soft delete
        site.save()
        return Response({'message': 'Site deactivated successfully'})


# ========== LOCATION MANAGEMENT VIEWS ==========

class LocationListView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, site_id=None):
        if site_id:
            locations = Location.objects.filter(site_id=site_id, is_active=True)
        else:
            locations = Location.objects.filter(is_active=True)
        
        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'Only superadmin can create locations'},
                          status=status.HTTP_403_FORBIDDEN)
        
        serializer = LocationSerializer(data=request.data)
        if serializer.is_valid():
            location = serializer.save()
            return Response(LocationSerializer(location).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ========== SECTION MANAGEMENT VIEWS ==========

class SectionListView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, location_id=None):
        if location_id:
            sections = Section.objects.filter(location_id=location_id, is_active=True)
        else:
            sections = Section.objects.filter(is_active=True)
        
        # Add capacity information
        serializer = SectionSerializer(sections, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'Only superadmin can create sections'},
                          status=status.HTTP_403_FORBIDDEN)
        
        serializer = SectionSerializer(data=request.data)
        if serializer.is_valid():
            section = serializer.save()
            return Response(SectionSerializer(section).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AvailableSectionsView(APIView):
    """Get all available sections for a given site (for visitor creation)"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, site_id):
        site = get_object_or_404(Site, pk=site_id, is_active=True)
        sections = Section.objects.filter(location__site=site, is_active=True).select_related('location')
        
        data = []
        for section in sections:
            data.append({
                'id': section.id,
                'name': section.name,
                'code': section.code,
                'location': section.location.name,
                'location_id': section.location.id,
                'section_type': section.section_type,
                'requires_escort': section.requires_escort,
                'daily_capacity': section.daily_capacity,
                'today_visitor_count': section.get_today_visitor_count(),
                'is_capacity_available': section.is_capacity_available()
            })
        
        return Response(data)
    

# ========== ACCESS MATRIX VIEW ==========

class VisitorAccessMatrixView(APIView):
    """Get complete access matrix for security personnel during check-in"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, visitor_id):
        visitor = get_object_or_404(Visitor, pk=visitor_id)
        
        # Security, creator, or superadmin can view
        if not (request.user.is_superuser or 
                visitor.created_by == request.user or
                visitor.selected_approvers.filter(id=request.user.id).exists()):
            return Response({'error': 'Access denied'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            'visitor': {
                'id': visitor.id,
                'full_name': visitor.full_name,
                'company_name': visitor.company_name,
                'photo': visitor.photo,
                'designated_check_in': visitor.designated_check_in,
                'designated_check_out': visitor.designated_check_out,
                'host_department': visitor.host_department,
                'meeting_room': visitor.meeting_room,
            },
            'access_matrix': visitor.get_access_matrix(),
            'summary': {
                'total_sections_requested': visitor.visitor_section_approvals.count(),
                'approved_sections': visitor.visitor_section_approvals.filter(status='approved').count(),
                'rejected_sections': visitor.visitor_section_approvals.filter(status='rejected').count(),
                'pending_sections': visitor.visitor_section_approvals.filter(status='pending').count(),
            }
        })
    

# ========== COOLDOWN MANAGEMENT VIEWS ==========

# pending -> super admin control on cooldown period

class CooldownPeriodListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        cooldowns = CooldownPeriod.objects.all().select_related('site', 'created_by')
        serializer = CooldownPeriodSerializer(cooldowns, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = CooldownPeriodSerializer(data=request.data)
        if serializer.is_valid():
            cooldown = serializer.save(created_by=request.user)
            return Response(CooldownPeriodSerializer(cooldown).data,
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CooldownPeriodDetailView(APIView):
    permission_classes = [IsAuthenticated,]
    
    def get(self, request, pk):
        cooldown = get_object_or_404(CooldownPeriod, pk=pk)
        serializer = CooldownPeriodSerializer(cooldown)
        return Response(serializer.data)
    
    def put(self, request, pk):
        cooldown = get_object_or_404(CooldownPeriod, pk=pk)
        serializer = CooldownPeriodSerializer(cooldown, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response(CooldownPeriodSerializer(updated).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        cooldown = get_object_or_404(CooldownPeriod, pk=pk)
        cooldown.delete()
        return Response({'message': 'Cooldown period deleted successfully'})


class SiteCooldownStatusView(APIView):
    """Check if a site is currently in cooldown - All employees"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, site_id):
        site = get_object_or_404(Site, pk=site_id)
        
        active_cooldown = None
        for cooldown in site.cooldowns.filter(is_active=True):
            if cooldown.is_active_now():
                active_cooldown = cooldown
                break
        
        if active_cooldown:
            return Response({
                'is_cooldown_active': True,
                'message': active_cooldown.get_active_message(),
                'cooldown_type': active_cooldown.cooldown_type,
                'start_datetime': active_cooldown.start_datetime,
                'end_datetime': active_cooldown.end_datetime,
            })
        
        return Response({
            'is_cooldown_active': False,
            'message': f'Site {site.name} is open for visitors',
            'daily_capacity_used': site.get_today_visitor_count(),
            'daily_capacity_limit': site.daily_capacity_limit,
            'capacity_remaining': site.daily_capacity_limit - site.get_today_visitor_count()
        })
    

class DailyCapacityLimitView(APIView):
    """
    Get daily capacity limit for a site or all sites.
    Use this for the Capacity Limit tile on dashboard.
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, site_id=None):
        if site_id:
            # Get single site capacity
            site = get_object_or_404(Site, pk=site_id, is_active=True)
            return Response({
                'site_id': site.id,
                'site_name': site.name,
                'daily_capacity_limit': site.daily_capacity_limit
            })
        else:
            # Get all sites capacity (for superadmin/overview)
            sites = Site.objects.filter(is_active=True)
            total_capacity = sum(site.daily_capacity_limit for site in sites)
            
            return Response({
                'total_sites': sites.count(),
                'total_daily_capacity': total_capacity,
                'sites': [
                    {
                        'site_id': site.id,
                        'site_name': site.name,
                        'daily_capacity_limit': site.daily_capacity_limit
                    }
                    for site in sites
                ]
            })


class TodayVisitorCountView(APIView):
    """
    Get today's visitor count for a site or all sites.
    Use this for the Today's Visitors tile on dashboard.
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, site_id=None):
        today = timezone.now().date()
        
        if site_id:
            # Get single site today's count
            site = get_object_or_404(Site, pk=site_id, is_active=True)
            
            today_visitors = Visitor.objects.filter(
                site=site,
                actual_check_in__date=today,
                status__in=['checked_in', 'checked_out']
            ).count()
            
            currently_inside = Visitor.objects.filter(
                site=site,
                status='checked_in'
            ).count()
            
            return Response({
                'site_id': site.id,
                'site_name': site.name,
                'date': today.isoformat(),
                'today_visitor_count': today_visitors,
                'currently_inside': currently_inside,
                'capacity_remaining': site.daily_capacity_limit - today_visitors,
                'is_cooldown_active': site.is_on_cooldown()
            })
        else:
            # Get all sites today's count (for superadmin/overview)
            sites = Site.objects.filter(is_active=True)
            
            site_stats = []
            total_visitors = 0
            total_capacity = 0
            
            for site in sites:
                today_visitors = Visitor.objects.filter(
                    site=site,
                    actual_check_in__date=today,
                    status__in=['checked_in', 'checked_out']
                ).count()
                
                total_visitors += today_visitors
                total_capacity += site.daily_capacity_limit
                
                site_stats.append({
                    'site_id': site.id,
                    'site_name': site.name,
                    'today_visitor_count': today_visitors,
                    'currently_inside': Visitor.objects.filter(site=site, status='checked_in').count(),
                    'capacity_remaining': site.daily_capacity_limit - today_visitors
                })
            
            return Response({
                'date': today.isoformat(),
                'total_visitors_today': total_visitors,
                'total_capacity': total_capacity,
                'overall_usage_percentage': round((total_visitors / total_capacity) * 100, 2) if total_capacity > 0 else 0,
                'sites': site_stats
            })


class VisitorCapacityStatusView(APIView):
    """
    Combined view for both capacity limit and today's count in one call.
    Useful if you want to make a single API call for both tiles.
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, site_id=None):
        today = timezone.now().date()
        
        if site_id:
            site = get_object_or_404(Site, pk=site_id, is_active=True)
            today_visitors = Visitor.objects.filter(
                site=site,
                actual_check_in__date=today,
                status__in=['checked_in', 'checked_out']
            ).count()
            
            return Response({
                'site': {
                    'id': site.id,
                    'name': site.name,
                    'daily_capacity_limit': site.daily_capacity_limit,
                    'today_visitor_count': today_visitors,
                    'currently_inside': Visitor.objects.filter(site=site, status='checked_in').count(),
                    'capacity_remaining': site.daily_capacity_limit - today_visitors,
                    'capacity_usage_percentage': round((today_visitors / site.daily_capacity_limit) * 100, 2) if site.daily_capacity_limit > 0 else 0,
                    'is_cooldown_active': site.is_on_cooldown()
                }
            })
        else:
            # Get user's primary site or default site
            # You can customize this logic based on your requirements
            user = request.user
            default_site = Site.objects.filter(is_active=True).first()
            
            if not default_site:
                return Response({'error': 'No active sites found'}, status=status.HTTP_404_NOT_FOUND)
            
            today_visitors = Visitor.objects.filter(
                site=default_site,
                actual_check_in__date=today,
                status__in=['checked_in', 'checked_out']
            ).count()
            
            return Response({
                'site': {
                    'id': default_site.id,
                    'name': default_site.name,
                    'daily_capacity_limit': default_site.daily_capacity_limit,
                    'today_visitor_count': today_visitors,
                    'currently_inside': Visitor.objects.filter(site=default_site, status='checked_in').count(),
                    'capacity_remaining': default_site.daily_capacity_limit - today_visitors,
                    'capacity_usage_percentage': round((today_visitors / default_site.daily_capacity_limit) * 100, 2) if default_site.daily_capacity_limit > 0 else 0,
                    'is_cooldown_active': default_site.is_on_cooldown()
                }
            })
