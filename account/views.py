from rest_framework.views import APIView
from rest_framework import request, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db import models
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from account.card_utils import IDCardGenerator
from .models import CooldownPeriod, Employee, Location, Section, Site, Visitor, VisitorApproval, VisitorSectionApproval, VisitorSectionRequest,VisitorSectionTracking

from .serializers import (
    CooldownPeriodSerializer, EmployeeSerializer, EmployeeListSerializer, EmployeeRegisterSerializer, LocationSerializer,
    LoginSerializer, SectionSerializer, SiteSerializer, VisitorCheckInSerializer, VisitorCheckOutSerializer, VisitorSectionApprovalSerializer, VisitorSectionTrackingSerializer, VisitorSerializer, VisitorApprovalResponseSerializer
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

# class VisitorListView(APIView):
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def get(self, request):
#         user = request.user
#         if user.is_superuser:
#             visitors = Visitor.objects.all()
#         else:
#             visitors = Visitor.objects.filter(
#                 models.Q(created_by=user) | 
#                 models.Q(selected_approvers=user)
#             ).distinct()
        
#         serializer = VisitorSerializer(visitors, many=True)
#         return Response(serializer.data)
    
#     def post(self, request):
#         """
#         Create a new visitor with sections and approvers.
        
#         Expected request body:
#         {
#             "full_name": "John Doe",
#             "email": "john@example.com",
#             "phone_number": "+1234567890",
#             "company_name": "ABC Corp",
#             "purpose_of_visit": "Meeting",
#             "site_id": 1,
#             "requested_section_ids": [1, 2, 3, 4],
#             "selected_approver_ids": [5, 6],
#             "designated_check_in": "2024-01-15T10:00:00Z",
#             "designated_check_out": "2024-01-15T17:00:00Z",
#             "vehicle_number": "ABC123",
#             "id_card_number": "ID123456",
#             "host_department": "IT",
#             "meeting_room": "Conference Room A"
#         }
#         """
#         data = request.data.copy()
        
#         # Validate site
#         site_id = data.get('site_id')
#         if not site_id:
#             return Response({'error': 'site_id is required'}, 
#                           status=status.HTTP_400_BAD_REQUEST)
        
#         site = get_object_or_404(Site, id=site_id, is_active=True)
        
#         # Check if site is in cooldown
#         if site.is_on_cooldown():
#             cooldown = site.get_active_cooldown()
#             return Response({
#                 'error': f'Cannot create visit. {cooldown.get_active_message()}'
#             }, status=status.HTTP_403_FORBIDDEN)
        
#         # Validate requested sections
#         requested_section_ids = data.get('requested_section_ids', [])
#         if not requested_section_ids:
#             return Response({'error': 'At least one section must be requested'}, 
#                           status=status.HTTP_400_BAD_REQUEST)
        
#         sections = Section.objects.filter(
#             id__in=requested_section_ids, 
#             location__site=site, 
#             is_active=True
#         )
#         if sections.count() != len(requested_section_ids):
#             return Response({'error': 'One or more sections are invalid or do not belong to the selected site'},
#                           status=status.HTTP_400_BAD_REQUEST)
        
#         # Check section capacities
#         for section in sections:
#             if not section.is_capacity_available():
#                 return Response({
#                     'error': f'Section "{section.name}" has reached its daily capacity ({section.daily_capacity})'
#                 }, status=status.HTTP_400_BAD_REQUEST)
        
#         # Validate approvers (at least 2)
#         approver_ids = data.get('selected_approver_ids', [])
#         if len(approver_ids) < 2:
#             return Response({'error': 'At least 2 approvers are required'}, 
#                           status=status.HTTP_400_BAD_REQUEST)
        
#         approvers = Employee.objects.filter(id__in=approver_ids, is_available=True)
#         if approvers.count() != len(approver_ids):
#             return Response({'error': 'One or more approvers are invalid'}, 
#                           status=status.HTTP_400_BAD_REQUEST)
        
#         # Remove non-model fields from data
#         data.pop('site_id', None)
#         data.pop('requested_section_ids', None)
#         data.pop('selected_approver_ids', None)
        
#         # Create visitor
#         visitor_serializer = VisitorSerializer(data=data)
#         if visitor_serializer.is_valid():
#             with transaction.atomic():
#                 visitor = visitor_serializer.save(created_by=request.user, site=site)
                
#                 # Add requested sections
#                 for section in sections:
#                     VisitorSectionRequest.objects.create(
#                         visitor=visitor,
#                         section=section,
#                         requested_by=request.user
#                     )
                
#                 # Add selected approvers
#                 visitor.selected_approvers.set(approvers)
                
#                 # Create section approval records for each approver and each section
#                 for approver in approvers:
#                     for section in sections:
#                         VisitorSectionApproval.objects.create(
#                             visitor=visitor,
#                             section=section,
#                             approver=approver,
#                             status='pending'
#                         )
                
#                 # Create legacy approval records (for backward compatibility)
#                 for approver in approvers:
#                     VisitorApproval.objects.create(
#                         visitor=visitor,
#                         approver=approver,
#                         status='pending'
#                     )
                
#                 # Send notifications
#                 from notification.utils import send_approval_request_notification
#                 for approver in approvers:
#                     send_approval_request_notification(approver, visitor)
            
#             return Response({
#                 'visitor': VisitorSerializer(visitor).data,
#                 'requested_sections': [{'id': s.id, 'name': s.name} for s in sections],
#                 'approvers': [{'id': a.id, 'name': a.full_name} for a in approvers]
#             }, status=status.HTTP_201_CREATED)
        
#         return Response(visitor_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class VisitorListView(APIView):
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def get(self, request):
#         user = request.user
#         if user.is_superuser:
#             visitors = Visitor.objects.all()
#         else:
#             visitors = Visitor.objects.filter(
#                 models.Q(created_by=user) | 
#                 models.Q(selected_approvers=user)
#             ).distinct()
        
#         serializer = VisitorSerializer(visitors, many=True)
        
#         # Add approval progress for each visitor
#         response_data = serializer.data
#         for i, visitor in enumerate(visitors):
#             response_data[i]['approval_progress'] = visitor.get_approval_progress()
#             response_data[i]['accessible_sections'] = [
#                 {'id': s.id, 'name': s.name} 
#                 for s in visitor.get_consensus_approved_sections()
#             ]
        
#         return Response(response_data)
    
#     def post(self, request):
#         """
#         Create a new visitor with sections and EXACTLY 2 approvers.
#         """
#         data = request.data.copy()
        
#         # Validate site
#         site_id = data.get('site_id')
#         if not site_id:
#             return Response({'error': 'site_id is required'}, 
#                         status=status.HTTP_400_BAD_REQUEST)
        
#         site = get_object_or_404(Site, id=site_id, is_active=True)
        
#         # Check if site is in cooldown
#         if hasattr(site, 'is_on_cooldown') and site.is_on_cooldown():
#             cooldown = site.get_active_cooldown()
#             return Response({
#                 'error': f'Cannot create visit. {cooldown.get_active_message()}'
#             }, status=status.HTTP_403_FORBIDDEN)
        
#         # Validate requested sections
#         requested_section_ids = data.get('requested_section_ids', [])
#         if not requested_section_ids:
#             return Response({'error': 'At least one section must be requested'}, 
#                         status=status.HTTP_400_BAD_REQUEST)
        
#         sections = Section.objects.filter(
#             id__in=requested_section_ids, 
#             location__site=site, 
#             is_active=True
#         )
#         if sections.count() != len(requested_section_ids):
#             return Response({'error': 'One or more sections are invalid or do not belong to the selected site'},
#                         status=status.HTTP_400_BAD_REQUEST)
        
#         # Check section capacities
#         for section in sections:
#             if hasattr(section, 'is_capacity_available') and not section.is_capacity_available():
#                 return Response({
#                     'error': f'Section "{section.name}" has reached its daily capacity ({section.daily_capacity})'
#                 }, status=status.HTTP_400_BAD_REQUEST)
        
#         # Validate EXACTLY 2 approvers
#         approver_ids = data.get('selected_approvers_ids', [])
#         if len(approver_ids) != 2:
#             return Response({
#                 'error': 'Exactly 2 approvers are required for consensus-based approval'
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         # Ensure approvers are not the same person
#         if approver_ids[0] == approver_ids[1]:
#             return Response({
#                 'error': 'The two approvers must be different employees'
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         approvers = Employee.objects.filter(id__in=approver_ids, is_available=True)
#         if approvers.count() != 2:
#             return Response({'error': 'Both approvers must be valid and available employees'}, 
#                         status=status.HTTP_400_BAD_REQUEST)
        
#         # Remove non-model fields from data
#         data.pop('site_id', None)
#         data.pop('requested_section_ids', None)
#         # DO NOT pop 'selected_approvers_ids' - let serializer handle it
        
#         # Create visitor - serializer will handle selected_approvers and VisitorApproval
#         visitor_serializer = VisitorSerializer(data=data)
#         if visitor_serializer.is_valid():
#             with transaction.atomic():
#                 # Save visitor (serializer's create method will create VisitorApproval records)
#                 visitor = visitor_serializer.save(
#                     created_by=request.user, 
#                     site=site,
#                     status='pending'
#                 )
                
#                 # Add requested sections
#                 for section in sections:
#                     VisitorSectionRequest.objects.create(
#                         visitor=visitor,
#                         section=section,
#                         requested_by=request.user
#                     )
                
#                 # Ensure correct approvers are set (in case serializer used different ones)
#                 visitor.selected_approvers.set(approvers)
                
#                 # Create section approval records for EACH approver and EACH section
#                 for approver in approvers:
#                     for section in sections:
#                         VisitorSectionApproval.objects.create(
#                             visitor=visitor,
#                             section=section,
#                             approver=approver,
#                             status='pending'
#                         )
                
#                 # REMOVE THIS BLOCK - Serializer already creates VisitorApproval
#                 # for approver in approvers:
#                 #     VisitorApproval.objects.create(
#                 #         visitor=visitor,
#                 #         approver=approver,
#                 #         status='pending'
#                 #     )
                
#                 # Send notifications to BOTH approvers
#                 from notification.utils import send_approval_request_notification
#                 for approver in approvers:
#                     send_approval_request_notification(
#                         approver, 
#                         visitor,
#                         sections=list(sections)
#                     )
            
#             progress = visitor.get_approval_progress()
            
#             return Response({
#                 'visitor': VisitorSerializer(visitor).data,
#                 'approval_mechanism': 'consensus_based',
#                 'message': 'Visitor created successfully! Both approvers must approve each section for access to be granted.',
#                 'approval_progress': progress,
#                 'requested_sections': [{'id': s.id, 'name': s.name, 'requires_escort': s.requires_escort} for s in sections],
#                 'approvers': [
#                     {'id': a.id, 'name': a.full_name, 'email': a.email, 'approver_number': i+1} 
#                     for i, a in enumerate(approvers)
#                 ],
#                 'consensus_rule': 'A section is accessible ONLY if BOTH approvers approve it.',
#                 'total_approvals_needed': 2 * len(sections)
#             }, status=status.HTTP_201_CREATED)
        
#         return Response(visitor_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ========== MODIFIED VISITOR CREATION VIEW ==========

# class VisitorListView(APIView):
#     permission_classes = [IsAuthenticated, IsEmployee]
#     parser_classes = [MultiPartParser, FormParser, JSONParser] 
    
#     def get(self, request):
#         user = request.user
#         if user.is_superuser:
#             visitors = Visitor.objects.all()
#         else:
#             visitors = Visitor.objects.filter(
#                 models.Q(created_by=user) | 
#                 models.Q(selected_approvers=user)
#             ).distinct()
        
#         serializer = VisitorSerializer(visitors, many=True)
        
#         # Add approval progress for each visitor
#         response_data = serializer.data
#         for i, visitor in enumerate(visitors):
#             response_data[i]['approval_progress'] = visitor.get_approval_progress()
#             response_data[i]['accessible_sections'] = [
#                 {'id': s.id, 'name': s.name} 
#                 for s in visitor.get_consensus_approved_sections()
#             ]
        
#         return Response(response_data)
    
#     def post(self, request):
#         """
#         Create a new visitor with sections and EXACTLY 2 approvers.
#         A section becomes accessible ONLY if BOTH approvers approve it.
#         Supports photo upload (file) or photo URL.
#         """
#         # Handle both JSON and multipart form data
#         if request.content_type and 'multipart' in request.content_type:
#             # For multipart form data, we need to handle differently
#             data = request.data.copy()
            
#             # CRITICAL: Add the uploaded file to data
#             if 'photo' in request.FILES:
#                 data['photo'] = request.FILES['photo']
            
#             # Parse array fields from form-data
#             # For requested_section_ids - get all values
#             if 'requested_section_ids' in request.POST:
#                 section_ids = request.POST.getlist('requested_section_ids')
#                 if section_ids:
#                     data['requested_section_ids'] = [int(x) for x in section_ids if x]
            
#             # Parse selected_approvers_ids - get all values
#             if 'selected_approvers_ids' in request.POST:
#                 approver_ids = request.POST.getlist('selected_approvers_ids')
#                 if approver_ids:
#                     data['selected_approvers_ids'] = [int(x) for x in approver_ids if x]
#         else:
#             data = request.data.copy()
#             # Handle photo URL if present (for JSON requests)
#             if 'photo' in request.FILES:
#                 data['photo'] = request.FILES['photo']
        
#         # Remove the photo from FILES after adding to data to avoid confusion
#         # (already handled above)
        
#         # Debug print to verify data
#         print("=" * 50)
#         print("Data keys:", data.keys())
#         print("Has photo in data:", 'photo' in data)
#         if 'photo' in data:
#             print("Photo type:", type(data['photo']))
#         print("Selected approvers:", data.get('selected_approvers_ids', []))
#         print("Requested sections:", data.get('requested_section_ids', []))
#         print("=" * 50)
        
#         # Validate site
#         site_id = data.get('site_id')
#         if not site_id:
#             return Response({'error': 'site_id is required'}, 
#                         status=status.HTTP_400_BAD_REQUEST)
        
#         site = get_object_or_404(Site, id=site_id, is_active=True)
        
#         # Check if site is in cooldown
#         if hasattr(site, 'is_on_cooldown') and site.is_on_cooldown():
#             cooldown = site.get_active_cooldown()
#             return Response({
#                 'error': f'Cannot create visit. {cooldown.get_active_message()}'
#             }, status=status.HTTP_403_FORBIDDEN)
        
#         # Validate requested sections
#         requested_section_ids = data.get('requested_section_ids', [])
#         if not requested_section_ids:
#             return Response({'error': 'At least one section must be requested'}, 
#                         status=status.HTTP_400_BAD_REQUEST)
        
#         # Ensure requested_section_ids is a list
#         if not isinstance(requested_section_ids, list):
#             requested_section_ids = [requested_section_ids]
        
#         sections = Section.objects.filter(
#             id__in=requested_section_ids, 
#             location__site=site, 
#             is_active=True
#         )
#         if sections.count() != len(requested_section_ids):
#             return Response({'error': 'One or more sections are invalid or do not belong to the selected site'},
#                         status=status.HTTP_400_BAD_REQUEST)
        
#         # Check section capacities
#         for section in sections:
#             if hasattr(section, 'is_capacity_available') and not section.is_capacity_available():
#                 return Response({
#                     'error': f'Section "{section.name}" has reached its daily capacity ({section.daily_capacity})'
#                 }, status=status.HTTP_400_BAD_REQUEST)
        
#         # CRITICAL: Validate EXACTLY 2 approvers
#         approver_ids = data.get('selected_approvers_ids', [])
        
#         # Ensure approver_ids is a list
#         if not isinstance(approver_ids, list):
#             approver_ids = [approver_ids]
        
#         if len(approver_ids) != 2:
#             return Response({
#                 'error': f'Exactly 2 approvers are required for consensus-based approval. Received {len(approver_ids)} approver(s): {approver_ids}'
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         # Ensure approvers are not the same person
#         if approver_ids[0] == approver_ids[1]:
#             return Response({
#                 'error': 'The two approvers must be different employees'
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         approvers = Employee.objects.filter(id__in=approver_ids, is_available=True)
#         if approvers.count() != 2:
#             return Response({'error': 'Both approvers must be valid and available employees'}, 
#                         status=status.HTTP_400_BAD_REQUEST)
        
#         # Remove non-model fields from data
#         data.pop('site_id', None)
#         data.pop('requested_section_ids', None)
#         # Keep selected_approvers_ids and photo for serializer
        
#         # Create visitor - serializer will handle everything including photo
#         visitor_serializer = VisitorSerializer(
#             data=data,
#             context={'sections': sections, 'request': request}
#         )
        
#         if visitor_serializer.is_valid():
#             with transaction.atomic():
#                 visitor = visitor_serializer.save(
#                     created_by=request.user, 
#                     site=site,
#                     status='pending'
#                 )
                
#                 # Create section tracking records
#                 for section in sections:
#                     VisitorSectionTracking.objects.get_or_create(
#                         visitor=visitor,
#                         section=section,
#                         defaults={'status': 'pending'}
#                     )
                
#                 # Calculate progress after all related objects are created
#                 progress = visitor.get_approval_progress()
                
#                 # Get photo display URL for response
#                 photo_display_url = None
#                 if visitor.photo and hasattr(visitor.photo, 'url'):
#                     photo_display_url = request.build_absolute_uri(visitor.photo.url)
#                 elif visitor.photo_url:
#                     photo_display_url = visitor.photo_url
            
#             # Prepare response
#             response_data = {
#                 'visitor': VisitorSerializer(visitor, context={'request': request}).data,
#                 'approval_mechanism': 'consensus_based',
#                 'message': 'Visitor created successfully! Both approvers must approve each section for access to be granted.',
#                 'approval_progress': progress,
#                 'requested_sections': [{'id': s.id, 'name': s.name, 'requires_escort': s.requires_escort} for s in sections],
#                 'approvers': [
#                     {'id': a.id, 'name': a.full_name, 'email': a.email, 'approver_number': i+1} 
#                     for i, a in enumerate(approvers)
#                 ],
#                 'consensus_rule': 'A section is accessible ONLY if BOTH approvers approve it.',
#                 'total_approvals_needed': 2 * len(sections),
#                 'photo_info': {
#                     'has_upload': bool(visitor.photo),
#                     'has_url': bool(visitor.photo_url),
#                     'display_url': photo_display_url,
#                     'source': 'upload' if visitor.photo else ('url' if visitor.photo_url else None)
#                 }
#             }
            
#             return Response(response_data, status=status.HTTP_201_CREATED)
        
#         # Print serializer errors for debugging
#         print("Serializer errors:", visitor_serializer.errors)
#         return Response(visitor_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     # def post(self, request):
#     #     """
#     #     Create a new visitor with sections and EXACTLY 2 approvers.
#     #     A section becomes accessible ONLY if BOTH approvers approve it.
#     #     """
#     #     data = request.data.copy()
        
#     #     # Validate site
#     #     site_id = data.get('site_id')
#     #     if not site_id:
#     #         return Response({'error': 'site_id is required'}, 
#     #                     status=status.HTTP_400_BAD_REQUEST)
        
#     #     site = get_object_or_404(Site, id=site_id, is_active=True)
        
#     #     # Check if site is in cooldown
#     #     if hasattr(site, 'is_on_cooldown') and site.is_on_cooldown():
#     #         cooldown = site.get_active_cooldown()
#     #         return Response({
#     #             'error': f'Cannot create visit. {cooldown.get_active_message()}'
#     #         }, status=status.HTTP_403_FORBIDDEN)
        
#     #     # Validate requested sections
#     #     requested_section_ids = data.get('requested_section_ids', [])
#     #     if not requested_section_ids:
#     #         return Response({'error': 'At least one section must be requested'}, 
#     #                     status=status.HTTP_400_BAD_REQUEST)
        
#     #     sections = Section.objects.filter(
#     #         id__in=requested_section_ids, 
#     #         location__site=site, 
#     #         is_active=True
#     #     )
#     #     if sections.count() != len(requested_section_ids):
#     #         return Response({'error': 'One or more sections are invalid or do not belong to the selected site'},
#     #                     status=status.HTTP_400_BAD_REQUEST)
        
#     #     # Check section capacities
#     #     for section in sections:
#     #         if hasattr(section, 'is_capacity_available') and not section.is_capacity_available():
#     #             return Response({
#     #                 'error': f'Section "{section.name}" has reached its daily capacity ({section.daily_capacity})'
#     #             }, status=status.HTTP_400_BAD_REQUEST)
        
#     #     # CRITICAL: Validate EXACTLY 2 approvers
#     #     approver_ids = data.get('selected_approvers_ids', [])
#     #     if len(approver_ids) != 2:
#     #         return Response({
#     #             'error': 'Exactly 2 approvers are required for consensus-based approval'
#     #         }, status=status.HTTP_400_BAD_REQUEST)
        
#     #     # Ensure approvers are not the same person
#     #     if approver_ids[0] == approver_ids[1]:
#     #         return Response({
#     #             'error': 'The two approvers must be different employees'
#     #         }, status=status.HTTP_400_BAD_REQUEST)
        
#     #     approvers = Employee.objects.filter(id__in=approver_ids, is_available=True)
#     #     if approvers.count() != 2:
#     #         return Response({'error': 'Both approvers must be valid and available employees'}, 
#     #                     status=status.HTTP_400_BAD_REQUEST)
        
#     #     # Remove non-model fields from data
#     #     data.pop('site_id', None)
#     #     data.pop('requested_section_ids', None)
#     #     # DO NOT pop 'selected_approvers_ids' - let serializer handle it
        
#     #     # Create visitor - serializer will handle everything
#     #     visitor_serializer = VisitorSerializer(
#     #         data=data,
#     #         context={'sections': sections, 'request': request}
#     #     )
        
#     #     if visitor_serializer.is_valid():
#     #         with transaction.atomic():
#     #             visitor = visitor_serializer.save(
#     #                 created_by=request.user, 
#     #                 site=site,
#     #                 status='pending'
#     #             )

                
#     #             for section in sections:
#     #                 VisitorSectionTracking.objects.get_or_create(
#     #                     visitor=visitor,
#     #                     section=section,
#     #                     defaults={'status': 'pending'}
#     #                 )
#     #             # Calculate progress after all related objects are created
#     #             progress = visitor.get_approval_progress()
            
#     #         return Response({
#     #             'visitor': VisitorSerializer(visitor).data,
#     #             'approval_mechanism': 'consensus_based',
#     #             'message': 'Visitor created successfully! Both approvers must approve each section for access to be granted.',
#     #             'approval_progress': progress,
#     #             'requested_sections': [{'id': s.id, 'name': s.name, 'requires_escort': s.requires_escort} for s in sections],
#     #             'approvers': [
#     #                 {'id': a.id, 'name': a.full_name, 'email': a.email, 'approver_number': i+1} 
#     #                 for i, a in enumerate(approvers)
#     #             ],
#     #             'consensus_rule': 'A section is accessible ONLY if BOTH approvers approve it.',
#     #             'total_approvals_needed': 2 * len(sections)
#     #         }, status=status.HTTP_201_CREATED)
        
#     #     return Response(visitor_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# account/views.py

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from .models import Visitor, Site, Section, Employee, VisitorSectionTracking
from .serializers import VisitorSerializer
from account.permissions import IsEmployee


class VisitorListView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get(self, request):
        user = request.user
        if user.is_superuser:
            visitors = Visitor.objects.all()
        else:
            visitors = Visitor.objects.filter(
                models.Q(created_by=user) | 
                models.Q(selected_approvers=user)
            ).distinct()
        
        serializer = VisitorSerializer(visitors, many=True, context={'request': request})
        
        # Add approval progress for each visitor
        response_data = serializer.data
        for i, visitor in enumerate(visitors):
            response_data[i]['approval_progress'] = visitor.get_approval_progress()
            response_data[i]['accessible_sections'] = [
                {'id': s.id, 'name': s.name} 
                for s in visitor.get_consensus_approved_sections()
            ]
        
        return Response(response_data)

    
    def post(self, request):
        """
        Create a new visitor with sections and EXACTLY 2 approvers.
        """
        # Initialize data dictionary
        data = {}
        
        # Handle different content types
        if request.content_type and 'multipart' in request.content_type:
            # For multipart form data
            for key, value in request.POST.items():
                data[key] = value
            
            # Handle file upload
            if 'photo' in request.FILES:
                data['photo'] = request.FILES['photo']
            
            # Parse array fields from form-data
            # For requested_section_ids - handle comma-separated strings
            if 'requested_section_ids' in data:
                value = data['requested_section_ids']
                # Check if it's a comma-separated string (from Flutter)
                if isinstance(value, str) and ',' in value:
                    data['requested_section_ids'] = [int(x.strip()) for x in value.split(',') if x.strip()]
                else:
                    # Try to get as list from POST (from Postman style)
                    section_ids = request.POST.getlist('requested_section_ids')
                    if section_ids and len(section_ids) > 0:
                        data['requested_section_ids'] = [int(x) for x in section_ids if x]
            
            # For selected_approvers_ids - handle comma-separated strings
            if 'selected_approvers_ids' in data:
                value = data['selected_approvers_ids']
                # Check if it's a comma-separated string (from Flutter)
                if isinstance(value, str) and ',' in value:
                    data['selected_approvers_ids'] = [int(x.strip()) for x in value.split(',') if x.strip()]
                else:
                    # Try to get as list from POST (from Postman style)
                    approver_ids = request.POST.getlist('selected_approvers_ids')
                    if approver_ids and len(approver_ids) > 0:
                        data['selected_approvers_ids'] = [int(x) for x in approver_ids if x]
        
        elif request.content_type and 'application/json' in request.content_type:
            # For JSON requests
            data = request.data.copy()
            
            # Ensure arrays are lists
            if 'requested_section_ids' in data and not isinstance(data['requested_section_ids'], list):
                data['requested_section_ids'] = [data['requested_section_ids']]
            
            if 'selected_approvers_ids' in data and not isinstance(data['selected_approvers_ids'], list):
                data['selected_approvers_ids'] = [data['selected_approvers_ids']]
        else:
            # Default fallback
            data = request.data.copy()
        
        # Debug print
        print("=" * 50)
        print("Content-Type:", request.content_type)
        print("Data keys:", list(data.keys()))
        print("Selected approvers_ids:", data.get('selected_approvers_ids'))
        print("Selected approvers_ids type:", type(data.get('selected_approvers_ids')))
        print("Requested section_ids:", data.get('requested_section_ids'))
        print("Requested section_ids type:", type(data.get('requested_section_ids')))
        print("Has photo:", 'photo' in data)
        print("=" * 50)
        
        # Validate site
        site_id = data.get('site_id')
        if not site_id:
            return Response({'error': 'site_id is required'}, 
                        status=status.HTTP_400_BAD_REQUEST)
        
        site = get_object_or_404(Site, id=site_id, is_active=True)
        
        # Check if site is in cooldown
        if hasattr(site, 'is_on_cooldown') and site.is_on_cooldown():
            cooldown = site.get_active_cooldown()
            return Response({
                'error': f'Cannot create visit. {cooldown.get_active_message()}'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Validate requested sections
        requested_section_ids = data.get('requested_section_ids', [])
        if not requested_section_ids:
            return Response({'error': 'At least one section must be requested'}, 
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure requested_section_ids is a list
        if not isinstance(requested_section_ids, list):
            requested_section_ids = [requested_section_ids]
        
        # Convert to integers if they're strings (handle single values)
        requested_section_ids = [int(x) if isinstance(x, str) and x.isdigit() else x for x in requested_section_ids]
        
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
            if hasattr(section, 'is_capacity_available') and not section.is_capacity_available():
                return Response({
                    'error': f'Section "{section.name}" has reached its daily capacity ({section.daily_capacity})'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # CRITICAL: Validate EXACTLY 2 approvers
        approver_ids = data.get('selected_approvers_ids', [])
        
        # Ensure approver_ids is a list
        if not isinstance(approver_ids, list):
            approver_ids = [approver_ids]
        
        # Convert to integers if they're strings
        approver_ids = [int(x) if isinstance(x, str) and x.isdigit() else x for x in approver_ids if x]
        
        if len(approver_ids) != 2:
            return Response({
                'error': f'Exactly 2 approvers are required for consensus-based approval. Received {len(approver_ids)} approver(s): {approver_ids}',
                'received_data': approver_ids
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure approvers are not the same person
        if approver_ids[0] == approver_ids[1]:
            return Response({
                'error': 'The two approvers must be different employees'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        approvers = Employee.objects.filter(id__in=approver_ids, is_available=True)
        if approvers.count() != 2:
            return Response({'error': 'Both approvers must be valid and available employees'}, 
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare data for serializer
        serializer_data = {}
        
        # Copy all relevant fields
        fields_to_copy = ['full_name', 'email', 'phone_number', 'purpose_of_visit', 
                        'company_name', 'designated_check_in', 'designated_check_out',
                        'vehicle_number', 'id_card_number', 'host_department', 
                        'meeting_room', 'check_in_notes', 'check_out_notes']
        
        for field in fields_to_copy:
            if field in data:
                serializer_data[field] = data[field]
        
        # Add photo or photo_url
        if 'photo' in data:
            serializer_data['photo'] = data['photo']
        elif 'photo_url' in data:
            serializer_data['photo_url'] = data['photo_url']
        
        # Add selected approvers IDs
        serializer_data['selected_approvers_ids'] = approver_ids
        
        # Debug print for serializer data
        print("Serializer data:", serializer_data)
        print("Selected approvers_ids in serializer data:", serializer_data.get('selected_approvers_ids'))
        
        # Create visitor - serializer will handle everything
        visitor_serializer = VisitorSerializer(
            data=serializer_data,
            context={'sections': sections, 'request': request}
        )
        
        if visitor_serializer.is_valid():
            with transaction.atomic():
                visitor = visitor_serializer.save(
                    created_by=request.user, 
                    site=site,
                    status='pending'
                )
                
                # Create section tracking records
                for section in sections:
                    VisitorSectionTracking.objects.get_or_create(
                        visitor=visitor,
                        section=section,
                        defaults={'status': 'pending'}
                    )
                
                # Calculate progress after all related objects are created
                progress = visitor.get_approval_progress()
                
                # Get photo display URL for response
                photo_display_url = None
                if visitor.photo and hasattr(visitor.photo, 'url'):
                    photo_display_url = request.build_absolute_uri(visitor.photo.url)
                elif visitor.photo_url:
                    photo_display_url = visitor.photo_url
            
            # Prepare response
            response_data = {
                'visitor': VisitorSerializer(visitor, context={'request': request}).data,
                'approval_mechanism': 'consensus_based',
                'message': 'Visitor created successfully!',
                'approval_progress': progress,
                'requested_sections': [{'id': s.id, 'name': s.name, 'requires_escort': s.requires_escort} for s in sections],
                'approvers': [
                    {'id': a.id, 'name': a.full_name, 'email': a.email, 'approver_number': i+1} 
                    for i, a in enumerate(approvers)
                ],
                'consensus_rule': 'A section is accessible ONLY if BOTH approvers approve it.',
                'total_approvals_needed': 2 * len(sections),
                'photo_info': {
                    'has_upload': bool(visitor.photo),
                    'has_url': bool(visitor.photo_url),
                    'display_url': photo_display_url
                }
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        # Print serializer errors for debugging
        print("Serializer errors:", visitor_serializer.errors)
        return Response(visitor_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # def post(self, request):
    #     """
    #     Create a new visitor with sections and EXACTLY 2 approvers.
    #     A section becomes accessible ONLY if BOTH approvers approve it.
    #     Supports either photo upload (file) OR photo URL, not both.
    #     """
    #     # Initialize data dictionary
    #     data = {}
        
    #     # Handle different content types
    #     if request.content_type and 'multipart' in request.content_type:
    #         # For multipart form data
    #         # Copy all POST data
    #         for key, value in request.POST.items():
    #             data[key] = value
            
    #         # Handle file upload
    #         if 'photo' in request.FILES:
    #             data['photo'] = request.FILES['photo']
            
    #         # Parse array fields from form-data
    #         # For requested_section_ids - get all values
    #         if 'requested_section_ids' in request.POST:
    #             section_ids = request.POST.getlist('requested_section_ids')
    #             if section_ids and len(section_ids) > 0:
    #                 data['requested_section_ids'] = [int(x) for x in section_ids if x]
            
    #         # For selected_approvers_ids - get all values
    #         if 'selected_approvers_ids' in request.POST:
    #             approver_ids = request.POST.getlist('selected_approvers_ids')
    #             if approver_ids and len(approver_ids) > 0:
    #                 data['selected_approvers_ids'] = [int(x) for x in approver_ids if x]
        
    #     elif request.content_type and 'application/json' in request.content_type:
    #         # For JSON requests
    #         data = request.data.copy()
            
    #         # Ensure arrays are lists
    #         if 'requested_section_ids' in data and not isinstance(data['requested_section_ids'], list):
    #             data['requested_section_ids'] = [data['requested_section_ids']]
            
    #         if 'selected_approvers_ids' in data and not isinstance(data['selected_approvers_ids'], list):
    #             data['selected_approvers_ids'] = [data['selected_approvers_ids']]
    #     else:
    #         # Default fallback
    #         data = request.data.copy()
        
    #     # Debug print to see what we have
    #     print("=" * 50)
    #     print("Content-Type:", request.content_type)
    #     print("Data keys:", list(data.keys()))
    #     print("Selected approvers_ids:", data.get('selected_approvers_ids'))
    #     print("Selected approvers_ids type:", type(data.get('selected_approvers_ids')))
    #     print("Requested section_ids:", data.get('requested_section_ids'))
    #     print("Has photo:", 'photo' in data)
    #     print("=" * 50)
        
    #     # Validate site
    #     site_id = data.get('site_id')
    #     if not site_id:
    #         return Response({'error': 'site_id is required'}, 
    #                     status=status.HTTP_400_BAD_REQUEST)
        
    #     site = get_object_or_404(Site, id=site_id, is_active=True)
        
    #     # Check if site is in cooldown
    #     if hasattr(site, 'is_on_cooldown') and site.is_on_cooldown():
    #         cooldown = site.get_active_cooldown()
    #         return Response({
    #             'error': f'Cannot create visit. {cooldown.get_active_message()}'
    #         }, status=status.HTTP_403_FORBIDDEN)
        
    #     # Validate requested sections
    #     requested_section_ids = data.get('requested_section_ids', [])
    #     if not requested_section_ids:
    #         return Response({'error': 'At least one section must be requested'}, 
    #                     status=status.HTTP_400_BAD_REQUEST)
        
    #     # Ensure requested_section_ids is a list
    #     if not isinstance(requested_section_ids, list):
    #         requested_section_ids = [requested_section_ids]
        
    #     # Convert to integers if they're strings
    #     requested_section_ids = [int(x) if isinstance(x, str) else x for x in requested_section_ids]
        
    #     sections = Section.objects.filter(
    #         id__in=requested_section_ids, 
    #         location__site=site, 
    #         is_active=True
    #     )
    #     if sections.count() != len(requested_section_ids):
    #         return Response({'error': 'One or more sections are invalid or do not belong to the selected site'},
    #                     status=status.HTTP_400_BAD_REQUEST)
        
    #     # Check section capacities
    #     for section in sections:
    #         if hasattr(section, 'is_capacity_available') and not section.is_capacity_available():
    #             return Response({
    #                 'error': f'Section "{section.name}" has reached its daily capacity ({section.daily_capacity})'
    #             }, status=status.HTTP_400_BAD_REQUEST)
        
    #     # CRITICAL: Validate EXACTLY 2 approvers
    #     approver_ids = data.get('selected_approvers_ids', [])
        
    #     # Ensure approver_ids is a list
    #     if not isinstance(approver_ids, list):
    #         approver_ids = [approver_ids]
        
    #     # Convert to integers if they're strings
    #     approver_ids = [int(x) if isinstance(x, str) else x for x in approver_ids if x]
        
    #     if len(approver_ids) != 2:
    #         return Response({
    #             'error': f'Exactly 2 approvers are required for consensus-based approval. Received {len(approver_ids)} approver(s): {approver_ids}'
    #         }, status=status.HTTP_400_BAD_REQUEST)
        
    #     # Ensure approvers are not the same person
    #     if approver_ids[0] == approver_ids[1]:
    #         return Response({
    #             'error': 'The two approvers must be different employees'
    #         }, status=status.HTTP_400_BAD_REQUEST)
        
    #     approvers = Employee.objects.filter(id__in=approver_ids, is_available=True)
    #     if approvers.count() != 2:
    #         return Response({'error': 'Both approvers must be valid and available employees'}, 
    #                     status=status.HTTP_400_BAD_REQUEST)
        
    #     # Prepare data for serializer
    #     serializer_data = {}
        
    #     # Copy all relevant fields
    #     fields_to_copy = ['full_name', 'email', 'phone_number', 'purpose_of_visit', 
    #                      'company_name', 'designated_check_in', 'designated_check_out',
    #                      'vehicle_number', 'id_card_number', 'host_department', 
    #                      'meeting_room', 'check_in_notes', 'check_out_notes']
        
    #     for field in fields_to_copy:
    #         if field in data:
    #             serializer_data[field] = data[field]
        
    #     # Add photo or photo_url
    #     if 'photo' in data:
    #         serializer_data['photo'] = data['photo']
    #     elif 'photo_url' in data:
    #         serializer_data['photo_url'] = data['photo_url']
        
    #     # Add selected approvers IDs
    #     serializer_data['selected_approvers_ids'] = approver_ids
        
    #     # Debug print for serializer data
    #     print("Serializer data:", serializer_data)
    #     print("Selected approvers_ids in serializer data:", serializer_data.get('selected_approvers_ids'))
        
    #     # Create visitor - serializer will handle everything
    #     visitor_serializer = VisitorSerializer(
    #         data=serializer_data,
    #         context={'sections': sections, 'request': request}
    #     )
        
    #     if visitor_serializer.is_valid():
    #         with transaction.atomic():
    #             visitor = visitor_serializer.save(
    #                 created_by=request.user, 
    #                 site=site,
    #                 status='pending'
    #             )
                
    #             # Create section tracking records
    #             for section in sections:
    #                 VisitorSectionTracking.objects.get_or_create(
    #                     visitor=visitor,
    #                     section=section,
    #                     defaults={'status': 'pending'}
    #                 )
                
    #             # Calculate progress after all related objects are created
    #             progress = visitor.get_approval_progress()
                
    #             # Get photo display URL for response
    #             photo_display_url = None
    #             if visitor.photo and hasattr(visitor.photo, 'url'):
    #                 photo_display_url = request.build_absolute_uri(visitor.photo.url)
    #             elif visitor.photo_url:
    #                 photo_display_url = visitor.photo_url
            
    #         # Prepare response
    #         response_data = {
    #             'visitor': VisitorSerializer(visitor, context={'request': request}).data,
    #             'approval_mechanism': 'consensus_based',
    #             'message': 'Visitor created successfully! Both approvers must approve each section for access to be granted.',
    #             'approval_progress': progress,
    #             'requested_sections': [{'id': s.id, 'name': s.name, 'requires_escort': s.requires_escort} for s in sections],
    #             'approvers': [
    #                 {'id': a.id, 'name': a.full_name, 'email': a.email, 'approver_number': i+1} 
    #                 for i, a in enumerate(approvers)
    #             ],
    #             'consensus_rule': 'A section is accessible ONLY if BOTH approvers approve it.',
    #             'total_approvals_needed': 2 * len(sections),
    #             'photo_info': {
    #                 'has_upload': bool(visitor.photo),
    #                 'has_url': bool(visitor.photo_url),
    #                 'display_url': photo_display_url
    #             }
    #         }
            
    #         return Response(response_data, status=status.HTTP_201_CREATED)
        
    #     # Print serializer errors for debugging
    #     print("Serializer errors:", visitor_serializer.errors)
    #     return Response(visitor_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VisitorDetailView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    # def get_visitor(self, pk, user):
    #     """Helper method to get visitor with permission check"""
    #     visitor = get_object_or_404(Visitor, pk=pk)
        
    #     # Check if user has permission to view this visitor
    #     if not (user.is_superuser or 
    #             visitor.created_by == user or 
    #             visitor.selected_approvers.filter(id=user.id).exists()):
    #         return None
    #     return visitor

    def get_visitor(self, pk, user):
        """Helper method to get visitor with permission check and prefetch related data"""
        from account.models import VisitorSectionApproval, VisitorSectionRequest, VisitorSectionTracking
        
        visitor = get_object_or_404(
            Visitor.objects.prefetch_related(
                'selected_approvers',
                'approved_by',
                'visitor_approvals',  # Changed from 'approval_responses' to 'visitor_approvals'
                'visitor_approvals__approver',  # Prefetch approver details
                # Prefetch section-related data
                'visitor_section_approvals__approver',
                'visitor_section_approvals__section',
                'section_requests__requested_by',
                'section_requests__section',
                'section_trackings__section',
                'section_trackings__section__location',
            ).select_related('created_by'),
            pk=pk
        )
        
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

# class VisitorSectionApprovalView(APIView):
#     """
#     Approve or reject SPECIFIC SECTIONS for a visitor.
#     Each approver can approve only the sections they deem necessary.
#     """
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, visitor_id):
#         visitor = get_object_or_404(Visitor, pk=visitor_id)
        
#         # Check if current user is an approver for this visitor
#         if not visitor.selected_approvers.filter(id=request.user.id).exists():
#             return Response(
#                 {'error': 'You are not authorized to approve sections for this visitor'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Request body format:
#         # {
#         #   "section_approvals": [
#         #       {"section_id": 1, "status": "approved", "comments": "OK to enter"},
#         #       {"section_id": 2, "status": "rejected", "rejection_reason": "No access needed"},
#         #       {"section_id": 3, "status": "approved", "comments": "Escort required"}
#         #   ]
#         # }
        
#         section_approvals = request.data.get('section_approvals', [])
        
#         if not section_approvals:
#             return Response(
#                 {'error': 'section_approvals list is required'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         results = []
        
#         with transaction.atomic():
#             for approval_data in section_approvals:
#                 section_id = approval_data.get('section_id')
#                 status_value = approval_data.get('status')
#                 comments = approval_data.get('comments', '')
#                 rejection_reason = approval_data.get('rejection_reason', '')
                
#                 if status_value not in ['approved', 'rejected']:
#                     results.append({
#                         'section_id': section_id,
#                         'status': 'error',
#                         'message': 'Status must be approved or rejected'
#                     })
#                     continue
                
#                 # Verify section belongs to this visitor's requested sections
#                 if not visitor.requested_sections.filter(id=section_id).exists():
#                     results.append({
#                         'section_id': section_id,
#                         'status': 'error',
#                         'message': 'Section not requested for this visitor'
#                     })
#                     continue
                
#                 # Get or create section approval record
#                 section_approval, created = VisitorSectionApproval.objects.get_or_create(
#                     visitor=visitor,
#                     section_id=section_id,
#                     approver=request.user,
#                     defaults={
#                         'status': status_value,
#                         'comments': comments,
#                         'rejection_reason': rejection_reason if status_value == 'rejected' else ''
#                     }
#                 )
                
#                 if not created and section_approval.status != 'pending':
#                     results.append({
#                         'section_id': section_id,
#                         'section_name': section_approval.section.name,
#                         'status': 'skipped',
#                         'message': f'Already {section_approval.status} by you'
#                     })
#                     continue
                
#                 # Update approval
#                 section_approval.status = status_value
#                 section_approval.comments = comments
                
#                 if status_value == 'rejected':
#                     if not rejection_reason:
#                         results.append({
#                             'section_id': section_id,
#                             'status': 'error',
#                             'message': 'Rejection reason required'
#                         })
#                         continue
#                     section_approval.rejection_reason = rejection_reason
#                 else:
#                     section_approval.approved_at = timezone.now()
#                     section_approval.approved_by = request.user
                
#                 section_approval.save()
                
#                 # Send notification for this section approval
#                 from notification.utils import send_section_approval_notification
#                 send_section_approval_notification(visitor, request.user, section_approval.section, status_value)
                
#                 results.append({
#                     'section_id': section_id,
#                     'section_name': section_approval.section.name,
#                     'status': status_value,
#                     'message': 'Success'
#                 })
            
#             # Update overall visitor status based on all section approvals
#             visitor.check_overall_approval_status()
        
#         # Get updated approval summary
#         total_sections = visitor.visitor_section_approvals.count()
#         approved_count = visitor.visitor_section_approvals.filter(status='approved').count()
#         rejected_count = visitor.visitor_section_approvals.filter(status='rejected').count()
#         pending_count = total_sections - approved_count - rejected_count
        
#         return Response({
#             'visitor_id': visitor.id,
#             'visitor_status': visitor.status,
#             'approval_summary': {
#                 'total_sections': total_sections,
#                 'approved': approved_count,
#                 'rejected': rejected_count,
#                 'pending': pending_count
#             },
#             'processed_sections': len(results),
#             'results': results
#         })

# isme kaam baaki hai abhi

# class VisitorSectionApprovalView(APIView):
#     """
#     Approve or reject sections with CONSENSUS logic.
#     A section becomes accessible ONLY when BOTH approvers approve it.
#     """
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, visitor_id):
#         visitor = get_object_or_404(Visitor, pk=visitor_id)
        
#         # Check if current user is an approver
#         if not visitor.selected_approvers.filter(id=request.user.id).exists():
#             return Response(
#                 {'error': 'You are not authorized to approve sections for this visitor'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Verify exactly 2 approvers exist
#         if visitor.selected_approvers.count() != 2:
#             return Response(
#                 {'error': 'Invalid configuration: Visitor does not have exactly 2 approvers'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         section_approvals = request.data.get('section_approvals', [])
        
#         if not section_approvals:
#             return Response(
#                 {'error': 'section_approvals list is required'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         previous_status = visitor.status
#         results = []
#         newly_consensus_approved_sections = []
        
#         # Get the other approver
#         other_approver = visitor.selected_approvers.exclude(id=request.user.id).first()
        
#         with transaction.atomic():
#             for approval_data in section_approvals:
#                 section_id = approval_data.get('section_id')
#                 status_value = approval_data.get('status')
#                 comments = approval_data.get('comments', '')
#                 rejection_reason = approval_data.get('rejection_reason', '')
                
#                 if status_value not in ['approved', 'rejected']:
#                     results.append({
#                         'section_id': section_id,
#                         'status': 'error',
#                         'message': 'Status must be approved or rejected'
#                     })
#                     continue
                
#                 # Verify section belongs to this visitor
#                 if not visitor.requested_sections.filter(id=section_id).exists():
#                     results.append({
#                         'section_id': section_id,
#                         'status': 'error',
#                         'message': 'Section not requested for this visitor'
#                     })
#                     continue
                
#                 # Get the section approval record
#                 try:
#                     section_approval = VisitorSectionApproval.objects.get(
#                         visitor=visitor,
#                         section_id=section_id,
#                         approver=request.user
#                     )
#                 except VisitorSectionApproval.DoesNotExist:
#                     results.append({
#                         'section_id': section_id,
#                         'status': 'error',
#                         'message': 'Approval record not found'
#                     })
#                     continue
                
#                 # Check if already responded
#                 if section_approval.status != 'pending':
#                     results.append({
#                         'section_id': section_id,
#                         'section_name': section_approval.section.name,
#                         'status': 'skipped',
#                         'message': f'Already {section_approval.status} by you'
#                     })
#                     continue
                
#                 # Update this approver's decision
#                 section_approval.status = status_value
#                 section_approval.comments = comments
#                 section_approval.responded_at = timezone.now()
                
#                 if status_value == 'rejected':
#                     if not rejection_reason:
#                         results.append({
#                             'section_id': section_id,
#                             'status': 'error',
#                             'message': 'Rejection reason required'
#                         })
#                         continue
#                     section_approval.rejection_reason = rejection_reason
#                 else:
#                     section_approval.approved_at = timezone.now()
#                     section_approval.approved_by = request.user
                
#                 section_approval.save()
                
#                 # Check if this section now has consensus approval (both approved)
#                 other_approval = VisitorSectionApproval.objects.get(
#                     visitor=visitor,
#                     section_id=section_id,
#                     approver=other_approver
#                 )
                
#                 has_consensus = (
#                     status_value == 'approved' and 
#                     other_approval.status == 'approved'
#                 )
                
#                 if has_consensus:
#                     newly_consensus_approved_sections.append({
#                         'id': section_approval.section.id,
#                         'name': section_approval.section.name,
#                         'requires_escort': section_approval.section.requires_escort
#                     })
                
#                 # Determine consensus status message
#                 if has_consensus:
#                     consensus_status = "CONSENSUS REACHED - Section accessible"
#                 elif status_value == 'approved' and other_approval.status == 'pending':
#                     consensus_status = "Approved by you - Waiting for other approver"
#                 elif status_value == 'approved' and other_approval.status == 'rejected':
#                     consensus_status = "Rejected by other approver - Section denied"
#                 elif status_value == 'rejected':
#                     consensus_status = "Rejected by you - Section denied"
#                 else:
#                     consensus_status = "⏳ Pending approval"
                
#                 results.append({
#                     'section_id': section_id,
#                     'section_name': section_approval.section.name,
#                     'your_decision': status_value,
#                     'other_approver_decision': other_approval.status,
#                     'has_consensus': has_consensus,
#                     'consensus_status': consensus_status,
#                     'requires_escort': section_approval.section.requires_escort,
#                     'message': f'Section {section_approval.section.name}: {consensus_status}'
#                 })
                
#                 # Send notification about this decision
#                 from notification.utils import send_section_approval_notification
#                 send_section_approval_notification(
#                     visitor, 
#                     request.user, 
#                     section_approval.section, 
#                     status_value,
#                     other_approver=other_approver,
#                     has_consensus=has_consensus
#                 )
            
#             # Update overall visitor status based on consensus
#             new_status = visitor.check_overall_approval_status()
            
#             # Get consensus approval progress
#             progress = visitor.get_approval_progress()
#             consensus_approved_sections = visitor.get_consensus_approved_sections()
            
#             # Send status change notifications if needed
#             if previous_status != new_status:
#                 from notification.utils import send_visitor_status_change_notification
                
#                 # Notify creator
#                 send_visitor_status_change_notification(
#                     visitor.created_by,
#                     visitor,
#                     previous_status,
#                     new_status,
#                     progress
#                 )
                
#                 # Notify other approver
#                 send_visitor_status_change_notification(
#                     other_approver,
#                     visitor,
#                     previous_status,
#                     new_status,
#                     progress
#                 )
        
#         # Prepare final response
#         response_data = {
#             'visitor_id': visitor.id,
#             'visitor_name': visitor.full_name,
#             'approval_mechanism': 'consensus_based',
#             'previous_status': previous_status,
#             'current_status': visitor.status,
#             'status_changed': previous_status != visitor.status,
#             'approval_progress': progress,
#             'consensus_approved_sections': [
#                 {'id': s.id, 'name': s.name, 'requires_escort': s.requires_escort}
#                 for s in consensus_approved_sections
#             ],
#             'newly_consensus_approved_sections': newly_consensus_approved_sections,
#             'processed_sections': results,
#             'your_remaining_pending': visitor.visitor_section_approvals.filter(
#                 approver=request.user, 
#                 status='pending'
#             ).count()
#         }
        
#         # Add appropriate message
#         if len(consensus_approved_sections) > 0:
#             response_data['message'] = (
#                 f"{len(consensus_approved_sections)} section(s) have been approved by BOTH approvers! "
#                 f"The visitor can now access: {', '.join([s['name'] for s in response_data['consensus_approved_sections']])}"
#             )
#         elif new_status == 'rejected':
#             response_data['message'] = "Visitor request has been rejected. Access denied for all sections."
#         elif progress['sections_partially_approved'] > 0:
#             response_data['message'] = (
#                 f"Your response recorded. {progress['sections_partially_approved']} section(s) have one approval and need the other approver's approval. "
#                 f"Remember: Sections need BOTH approvers to approve for access to be granted."
#             )
#         else:
#             response_data['message'] = (
#                 f"Your response recorded. Waiting for {progress['total_approvers']} approver(s) to respond. "
#                 f"Both approvers must approve each section."
#             )
        
#         return Response(response_data)


# In your views.py, update your section approval endpoint:

# class VisitorSectionApprovalView(APIView):
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, visitor_id, section_id):
#         try:
#             visitor = Visitor.objects.get(id=visitor_id)
#             section = Section.objects.get(id=section_id)
            
#             # Check authorization
#             if not visitor.selected_approvers.filter(id=request.user.id).exists():
#                 return Response(
#                     {'error': 'You are not authorized to approve this visitor'},
#                     status=status.HTTP_403_FORBIDDEN
#                 )
            
#             # Get or create section approval
#             section_approval, created = VisitorSectionApproval.objects.get_or_create(
#                 visitor=visitor,
#                 section=section,
#                 approver=request.user,
#                 defaults={'status': 'pending'}
#             )
            
#             # Update status
#             new_status = request.data.get('status')
#             comments = request.data.get('comments', '')
            
#             if new_status not in ['approved', 'rejected']:
#                 return Response(
#                     {'error': 'Invalid status'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             section_approval.status = new_status
#             section_approval.comments = comments
#             if new_status == 'rejected':
#                 section_approval.rejection_reason = request.data.get('rejection_reason', comments)
#             section_approval.responded_at = timezone.now()
#             if new_status == 'approved':
#                 section_approval.approved_at = timezone.now()
#                 section_approval.approved_by = request.user
#             section_approval.save()
            
#             # CRITICAL: Update the overall visitor approval status for this approver
#             visitor.update_approver_status(request.user)
            
#             # CRITICAL: Update the overall visitor status
#             visitor.update_overall_visitor_status()
            
#             return Response({
#                 'message': f'Section {new_status} successfully',
#                 'section_approval': VisitorSectionApprovalSerializer(section_approval).data,
#                 'visitor_status': visitor.status
#             })
            
#         except Visitor.DoesNotExist:
#             return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)
#         except Section.DoesNotExist:
#             return Response({'error': 'Section not found'}, status=status.HTTP_404_NOT_FOUND)


# account/views.py - Update your VisitorSectionApprovalView

# class VisitorSectionApprovalView(APIView):
#     """
#     Approve or reject sections for a visitor.
#     URL: /account/api/visitors/{visitor_id}/approve-sections/
#     Body: {
#         "section_approvals": [
#             {"section_id": 1, "status": "approved", "comments": "Approved"},
#             {"section_id": 2, "status": "rejected", "comments": "No access needed"}
#         ]
#     }
#     """
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, visitor_id):
#         try:
#             visitor = Visitor.objects.get(id=visitor_id)
            
#             # Check authorization
#             if not visitor.selected_approvers.filter(id=request.user.id).exists():
#                 return Response(
#                     {'error': 'You are not authorized to approve sections for this visitor'},
#                     status=status.HTTP_403_FORBIDDEN
#                 )
            
#             # Get section approvals from request body
#             section_approvals = request.data.get('section_approvals', [])
            
#             if not section_approvals:
#                 return Response(
#                     {'error': 'section_approvals list is required'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             results = []
#             total_approved = 0
#             total_rejected = 0
            
#             with transaction.atomic():
#                 for approval_data in section_approvals:
#                     section_id = approval_data.get('section_id')
#                     new_status = approval_data.get('status')
#                     comments = approval_data.get('comments', '')
#                     rejection_reason = approval_data.get('rejection_reason', '')
                    
#                     # Validate status
#                     if new_status not in ['approved', 'rejected']:
#                         results.append({
#                             'section_id': section_id,
#                             'status': 'error',
#                             'message': 'Status must be approved or rejected'
#                         })
#                         continue
                    
#                     # Verify section exists
#                     try:
#                         section = Section.objects.get(id=section_id, is_active=True)
#                     except Section.DoesNotExist:
#                         results.append({
#                             'section_id': section_id,
#                             'status': 'error',
#                             'message': 'Section not found'
#                         })
#                         continue
                    
#                     # Check if section belongs to visitor's site
#                     if section.location.site_id != visitor.site_id:
#                         results.append({
#                             'section_id': section_id,
#                             'section_name': section.name,
#                             'status': 'error',
#                             'message': f'Section {section.name} does not belong to visitor\'s site'
#                         })
#                         continue
                    
#                     # Get or create section approval
#                     section_approval, created = VisitorSectionApproval.objects.get_or_create(
#                         visitor=visitor,
#                         section=section,
#                         approver=request.user,
#                         defaults={'status': 'pending'}
#                     )
                    
#                     # Check if already responded
#                     if not created and section_approval.status != 'pending':
#                         results.append({
#                             'section_id': section_id,
#                             'section_name': section.name,
#                             'status': 'skipped',
#                             'message': f'Already {section_approval.status} by you'
#                         })
#                         continue
                    
#                     # Update approval
#                     section_approval.status = new_status
#                     section_approval.comments = comments
#                     section_approval.responded_at = timezone.now()
                    
#                     if new_status == 'approved':
#                         section_approval.approved_at = timezone.now()
#                         section_approval.approved_by = request.user
#                         total_approved += 1
#                     elif new_status == 'rejected':
#                         section_approval.rejection_reason = rejection_reason or comments
#                         total_rejected += 1
                    
#                     section_approval.save()
                    
#                     results.append({
#                         'section_id': section_id,
#                         'section_name': section.name,
#                         'status': new_status,
#                         'message': f'Section {section.name} {new_status} successfully'
#                     })
                    
#                     # Send notification for this section approval
#                     from notification.utils import send_section_approval_notification
#                     send_section_approval_notification(
#                         visitor, 
#                         request.user, 
#                         section, 
#                         new_status
#                     )
                
#                 # Update the overall visitor approval status for this approver
#                 visitor.update_approver_status(request.user)
                
#                 # Update the overall visitor status
#                 visitor.update_overall_visitor_status()
            
#             # Get updated progress
#             approval_progress = visitor.get_approval_progress()
#             consensus_approved_sections = visitor.get_consensus_approved_sections()
            
#             return Response({
#                 'success': True,
#                 'message': f'Processed {len(results)} section(s). Approved: {total_approved}, Rejected: {total_rejected}',
#                 'visitor_id': visitor.id,
#                 'visitor_status': visitor.status,
#                 'approval_progress': approval_progress,
#                 'consensus_approved_sections': [
#                     {'id': s.id, 'name': s.name, 'requires_escort': s.requires_escort}
#                     for s in consensus_approved_sections
#                 ],
#                 'results': results
#             })
            
#         except Visitor.DoesNotExist:
#             return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# account/views.py - Update your active VisitorSectionApprovalView with notifications

# class VisitorSectionApprovalView(APIView):
#     """
#     Approve or reject sections for a visitor.
#     URL: /account/api/visitors/{visitor_id}/approve-sections/
#     Body: {
#         "section_approvals": [
#             {"section_id": 1, "status": "approved", "comments": "Approved"},
#             {"section_id": 2, "status": "rejected", "comments": "No access needed"}
#         ]
#     }
#     """
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, visitor_id):
#         try:
#             visitor = Visitor.objects.get(id=visitor_id)
            
#             # Check authorization
#             if not visitor.selected_approvers.filter(id=request.user.id).exists():
#                 return Response(
#                     {'error': 'You are not authorized to approve sections for this visitor'},
#                     status=status.HTTP_403_FORBIDDEN
#                 )
            
#             # Get section approvals from request body
#             section_approvals = request.data.get('section_approvals', [])
            
#             if not section_approvals:
#                 return Response(
#                     {'error': 'section_approvals list is required'},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             previous_status = visitor.status
#             results = []
#             total_approved = 0
#             total_rejected = 0
#             newly_consensus_approved_sections = []
            
#             # Get the other approver (for consensus)
#             other_approver = visitor.selected_approvers.exclude(id=request.user.id).first()
            
#             with transaction.atomic():
#                 for approval_data in section_approvals:
#                     section_id = approval_data.get('section_id')
#                     new_status = approval_data.get('status')
#                     comments = approval_data.get('comments', '')
#                     rejection_reason = approval_data.get('rejection_reason', '')
                    
#                     # Validate status
#                     if new_status not in ['approved', 'rejected']:
#                         results.append({
#                             'section_id': section_id,
#                             'status': 'error',
#                             'message': 'Status must be approved or rejected'
#                         })
#                         continue
                    
#                     # Verify section exists
#                     try:
#                         section = Section.objects.get(id=section_id, is_active=True)
#                     except Section.DoesNotExist:
#                         results.append({
#                             'section_id': section_id,
#                             'status': 'error',
#                             'message': 'Section not found'
#                         })
#                         continue
                    
#                     # Check if section belongs to visitor's site
#                     if section.location.site_id != visitor.site_id:
#                         results.append({
#                             'section_id': section_id,
#                             'section_name': section.name,
#                             'status': 'error',
#                             'message': f'Section {section.name} does not belong to visitor\'s site'
#                         })
#                         continue
                    
#                     # Get or create section approval
#                     section_approval, created = VisitorSectionApproval.objects.get_or_create(
#                         visitor=visitor,
#                         section=section,
#                         approver=request.user,
#                         defaults={'status': 'pending'}
#                     )
                    
#                     # Check if already responded
#                     if not created and section_approval.status != 'pending':
#                         results.append({
#                             'section_id': section_id,
#                             'section_name': section.name,
#                             'status': 'skipped',
#                             'message': f'Already {section_approval.status} by you'
#                         })
#                         continue
                    
#                     # Update approval
#                     section_approval.status = new_status
#                     section_approval.comments = comments
#                     section_approval.responded_at = timezone.now()
                    
#                     if new_status == 'approved':
#                         section_approval.approved_at = timezone.now()
#                         section_approval.approved_by = request.user
#                         total_approved += 1
#                     elif new_status == 'rejected':
#                         section_approval.rejection_reason = rejection_reason or comments
#                         total_rejected += 1
                    
#                     section_approval.save()
                    
#                     # Check consensus status (for 2 approver system)
#                     has_consensus = False
#                     other_approval_status = 'pending'
                    
#                     if other_approver:
#                         other_approval = VisitorSectionApproval.objects.get(
#                             visitor=visitor,
#                             section=section,
#                             approver=other_approver
#                         )
#                         other_approval_status = other_approval.status
                        
#                         # Consensus reached when BOTH approvers approved
#                         has_consensus = (new_status == 'approved' and other_approval.status == 'approved')
                        
#                         if has_consensus:
#                             newly_consensus_approved_sections.append({
#                                 'id': section.id,
#                                 'name': section.name,
#                                 'requires_escort': section.requires_escort
#                             })
                    
#                     results.append({
#                         'section_id': section_id,
#                         'section_name': section.name,
#                         'status': new_status,
#                         'has_consensus': has_consensus,
#                         'other_approver_status': other_approval_status,
#                         'message': f'Section {section.name} {new_status} successfully'
#                     })
                    
#                     # ========== SEND WEBSOCKET NOTIFICATION ==========
#                     from notification.utils import send_section_approval_notification
                    
#                     # Send notification about this decision
#                     send_section_approval_notification(
#                         visitor, 
#                         request.user, 
#                         section, 
#                         new_status,
#                         other_approver=other_approver,
#                         has_consensus=has_consensus
#                     )
                    
#                     # Also create a database notification
#                     from notification.models import Notification
                    
#                     # Notify the visitor creator
#                     Notification.objects.create(
#                         recipient=visitor.created_by,
#                         notification_type='section_approval_update',
#                         title=f'Section {new_status}: {section.name}',
#                         message=f'{request.user.full_name} has {new_status} access to {section.name} for {visitor.full_name}',
#                         data={
#                             'visitor_id': visitor.id,
#                             'visitor_name': visitor.full_name,
#                             'section_id': section.id,
#                             'section_name': section.name,
#                             'status': new_status,
#                             'has_consensus': has_consensus,
#                             'approved_by': request.user.full_name
#                         }
#                     )
                    
#                     # Notify the other approver (if exists and not the current user)
#                     if other_approver and other_approver.id != request.user.id:
#                         Notification.objects.create(
#                             recipient=other_approver,
#                             notification_type='section_approval_update',
#                             title=f'Other approver {new_status}: {section.name}',
#                             message=f'{request.user.full_name} has {new_status} access to {section.name} for {visitor.full_name}',
#                             data={
#                                 'visitor_id': visitor.id,
#                                 'visitor_name': visitor.full_name,
#                                 'section_id': section.id,
#                                 'section_name': section.name,
#                                 'status': new_status,
#                                 'has_consensus': has_consensus,
#                                 'approved_by': request.user.full_name
#                             }
#                         )
                
#                 # Update the overall visitor approval status for this approver
#                 visitor.update_approver_status(request.user)
                
#                 # Update the overall visitor status
#                 new_status = visitor.update_overall_visitor_status()
                
#                 # Get consensus approval progress
#                 progress = visitor.get_approval_progress()
#                 consensus_approved_sections = visitor.get_consensus_approved_sections()
                
#                 # ========== SEND STATUS CHANGE NOTIFICATIONS ==========
#                 if previous_status != new_status:
#                     from notification.utils import send_visitor_status_change_notification
                    
#                     # Notify creator
#                     send_visitor_status_change_notification(
#                         visitor.created_by,
#                         visitor,
#                         previous_status,
#                         new_status,
#                         progress
#                     )
                    
#                     # Notify both approvers
#                     for approver in visitor.selected_approvers.all():
#                         send_visitor_status_change_notification(
#                             approver,
#                             visitor,
#                             previous_status,
#                             new_status,
#                             progress
#                         )
                    
#                     # Also create database notifications for status change
#                     from notification.models import Notification
                    
#                     status_message = {
#                         'approved': 'fully approved',
#                         'rejected': 'rejected',
#                         'partially_approved': 'partially approved',
#                         'pending': 'still pending'
#                     }.get(new_status, new_status)
                    
#                     Notification.objects.create(
#                         recipient=visitor.created_by,
#                         notification_type='visitor_status_change',
#                         title=f'Visitor Status Updated: {visitor.full_name}',
#                         message=f'Visitor request has been {status_message}. {progress["accessible_sections_count"]} out of {progress["total_sections"]} sections are accessible.',
#                         data={
#                             'visitor_id': visitor.id,
#                             'visitor_name': visitor.full_name,
#                             'previous_status': previous_status,
#                             'current_status': new_status,
#                             'approval_progress': progress
#                         }
#                     )
            
#             # Prepare final response
#             response_data = {
#                 'success': True,
#                 'message': f'Processed {len(results)} section(s). Approved: {total_approved}, Rejected: {total_rejected}',
#                 'visitor_id': visitor.id,
#                 'visitor_status': visitor.status,
#                 'previous_status': previous_status,
#                 'status_changed': previous_status != visitor.status,
#                 'approval_progress': progress,
#                 'consensus_approved_sections': [
#                     {'id': s.id, 'name': s.name, 'requires_escort': s.requires_escort}
#                     for s in consensus_approved_sections
#                 ],
#                 'newly_consensus_approved_sections': newly_consensus_approved_sections,
#                 'results': results
#             }
            
#             # Add appropriate message
#             if len(consensus_approved_sections) > 0 and newly_consensus_approved_sections:
#                 response_data['message'] = (
#                     f"🎉 {len(newly_consensus_approved_sections)} new section(s) have been approved by BOTH approvers! "
#                     f"The visitor can now access: {', '.join([s['name'] for s in newly_consensus_approved_sections])}"
#                 )
#             elif new_status == 'rejected':
#                 response_data['message'] = "Visitor request has been rejected. Access denied for all sections."
#             elif progress.get('sections_partially_approved', 0) > 0:
#                 response_data['message'] = (
#                     f"Your response recorded. {progress['sections_partially_approved']} section(s) have one approval and need the other approver's approval. "
#                     f"Sections need BOTH approvers to approve for access to be granted."
#                 )
#             else:
#                 response_data['message'] = (
#                     f"Your response recorded. Waiting for other approver(s) to respond. "
#                     f"Both approvers must approve each section."
#                 )
            
#             return Response(response_data)
            
#         except Visitor.DoesNotExist:
#             return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# account/views.py - Updated VisitorSectionApprovalView

class VisitorSectionApprovalView(APIView):
    """
    Approve or reject sections for a visitor.
    URL: /account/api/visitors/{visitor_id}/approve-sections/
    Body: {
        "section_approvals": [
            {"section_id": 1, "status": "approved", "comments": "Approved"},
            {"section_id": 2, "status": "rejected", "comments": "No access needed"}
        ]
    }
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request, visitor_id):
        try:
            visitor = Visitor.objects.get(id=visitor_id)
            
            # Check authorization
            if not visitor.selected_approvers.filter(id=request.user.id).exists():
                return Response(
                    {'error': 'You are not authorized to approve sections for this visitor'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get section approvals from request body
            section_approvals = request.data.get('section_approvals', [])
            
            if not section_approvals:
                return Response(
                    {'error': 'section_approvals list is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            previous_status = visitor.status
            results = []
            total_approved = 0
            total_rejected = 0
            newly_consensus_approved_sections = []
            
            # Get the other approver (for consensus)
            other_approver = visitor.selected_approvers.exclude(id=request.user.id).first()
            
            with transaction.atomic():
                for approval_data in section_approvals:
                    section_id = approval_data.get('section_id')
                    new_status = approval_data.get('status')
                    comments = approval_data.get('comments', '')
                    rejection_reason = approval_data.get('rejection_reason', '')
                    
                    # Validate status
                    if new_status not in ['approved', 'rejected']:
                        results.append({
                            'section_id': section_id,
                            'status': 'error',
                            'message': 'Status must be approved or rejected'
                        })
                        continue
                    
                    # Verify section exists
                    try:
                        section = Section.objects.get(id=section_id, is_active=True)
                    except Section.DoesNotExist:
                        results.append({
                            'section_id': section_id,
                            'status': 'error',
                            'message': 'Section not found'
                        })
                        continue
                    
                    # Check if section belongs to visitor's site
                    if section.location.site_id != visitor.site_id:
                        results.append({
                            'section_id': section_id,
                            'section_name': section.name,
                            'status': 'error',
                            'message': f'Section {section.name} does not belong to visitor\'s site'
                        })
                        continue
                    
                    # Get or create section approval
                    section_approval, created = VisitorSectionApproval.objects.get_or_create(
                        visitor=visitor,
                        section=section,
                        approver=request.user,
                        defaults={'status': 'pending'}
                    )
                    
                    # Check if already responded
                    if not created and section_approval.status != 'pending':
                        results.append({
                            'section_id': section_id,
                            'section_name': section.name,
                            'status': 'skipped',
                            'message': f'Already {section_approval.status} by you'
                        })
                        continue
                    
                    # Update approval
                    section_approval.status = new_status
                    section_approval.comments = comments
                    section_approval.responded_at = timezone.now()
                    
                    if new_status == 'approved':
                        section_approval.approved_at = timezone.now()
                        section_approval.approved_by = request.user
                        total_approved += 1
                    elif new_status == 'rejected':
                        section_approval.rejection_reason = rejection_reason or comments
                        total_rejected += 1
                    
                    section_approval.save()
                    
                    # Check consensus status (for 2 approver system)
                    has_consensus = False
                    other_approval_status = 'pending'
                    
                    if other_approver:
                        other_approval = VisitorSectionApproval.objects.get(
                            visitor=visitor,
                            section=section,
                            approver=other_approver
                        )
                        other_approval_status = other_approval.status
                        
                        # Consensus reached when BOTH approvers approved
                        has_consensus = (new_status == 'approved' and other_approval.status == 'approved')
                        
                        if has_consensus:
                            newly_consensus_approved_sections.append({
                                'id': section.id,
                                'name': section.name,
                                'requires_escort': section.requires_escort
                            })
                    
                    results.append({
                        'section_id': section_id,
                        'section_name': section.name,
                        'status': new_status,
                        'has_consensus': has_consensus,
                        'other_approver_status': other_approval_status,
                        'message': f'Section {section.name} {new_status} successfully'
                    })
                    
                    # ========== SEND WEBSOCKET NOTIFICATION ==========
                    from notification.utils import send_section_approval_notification
                    
                    # Send notification about this decision
                    send_section_approval_notification(
                        visitor, 
                        request.user, 
                        section, 
                        new_status,
                        other_approver=other_approver,
                        has_consensus=has_consensus
                    )
                    
                    # Also create a database notification
                    from notification.models import Notification
                    
                    # Notify the visitor creator
                    Notification.objects.create(
                        recipient=visitor.created_by,
                        notification_type='section_approval_update',
                        title=f'Section {new_status}: {section.name}',
                        message=f'{request.user.full_name} has {new_status} access to {section.name} for {visitor.full_name}',
                        data={
                            'visitor_id': visitor.id,
                            'visitor_name': visitor.full_name,
                            'section_id': section.id,
                            'section_name': section.name,
                            'status': new_status,
                            'has_consensus': has_consensus,
                            'approved_by': request.user.full_name
                        }
                    )
                    
                    # Notify the other approver (if exists and not the current user)
                    if other_approver and other_approver.id != request.user.id:
                        Notification.objects.create(
                            recipient=other_approver,
                            notification_type='section_approval_update',
                            title=f'Other approver {new_status}: {section.name}',
                            message=f'{request.user.full_name} has {new_status} access to {section.name} for {visitor.full_name}',
                            data={
                                'visitor_id': visitor.id,
                                'visitor_name': visitor.full_name,
                                'section_id': section.id,
                                'section_name': section.name,
                                'status': new_status,
                                'has_consensus': has_consensus,
                                'approved_by': request.user.full_name
                            }
                        )
                
                # Update the overall visitor approval status for this approver
                visitor.update_approver_status(request.user)
                
                # Update the overall visitor status
                new_status = visitor.update_overall_visitor_status()
                
                # Get consensus approval progress
                progress = visitor.get_approval_progress()
                consensus_approved_sections = visitor.get_consensus_approved_sections()
                
                # ========== SEND STATUS CHANGE NOTIFICATIONS ==========
                if previous_status != new_status:
                    from notification.utils import send_visitor_status_change_notification
                    
                    # Notify creator
                    send_visitor_status_change_notification(
                        visitor.created_by,
                        visitor,
                        previous_status,
                        new_status,
                        progress
                    )
                    
                    # Notify both approvers
                    for approver in visitor.selected_approvers.all():
                        send_visitor_status_change_notification(
                            approver,
                            visitor,
                            previous_status,
                            new_status,
                            progress
                        )
                    
                    # Also create database notifications for status change
                    from notification.models import Notification
                    
                    status_message = {
                        'approved': 'fully approved',
                        'rejected': 'rejected',
                        'partially_approved': 'partially approved',
                        'pending': 'still pending'
                    }.get(new_status, new_status)
                    
                    # FIXED: Use .get() with fallback to avoid KeyError
                    accessible_count = progress.get('accessible_sections_count', progress.get('sections_accessible', 0))
                    total_sections = progress.get('total_sections', 0)
                    
                    Notification.objects.create(
                        recipient=visitor.created_by,
                        notification_type='visitor_status_change',
                        title=f'Visitor Status Updated: {visitor.full_name}',
                        message=f'Visitor request has been {status_message}. {accessible_count} out of {total_sections} sections are accessible.',
                        data={
                            'visitor_id': visitor.id,
                            'visitor_name': visitor.full_name,
                            'previous_status': previous_status,
                            'current_status': new_status,
                            'approval_progress': progress
                        }
                    )
            
            # Prepare final response
            response_data = {
                'success': True,
                'message': f'Processed {len(results)} section(s). Approved: {total_approved}, Rejected: {total_rejected}',
                'visitor_id': visitor.id,
                'visitor_status': visitor.status,
                'previous_status': previous_status,
                'status_changed': previous_status != visitor.status,
                'approval_progress': progress,
                'consensus_approved_sections': [
                    {'id': s.id, 'name': s.name, 'requires_escort': s.requires_escort}
                    for s in consensus_approved_sections
                ],
                'newly_consensus_approved_sections': newly_consensus_approved_sections,
                'results': results
            }
            
            # Add appropriate message using safe dictionary access
            if len(consensus_approved_sections) > 0 and newly_consensus_approved_sections:
                response_data['message'] = (
                    f"🎉 {len(newly_consensus_approved_sections)} new section(s) have been approved by BOTH approvers! "
                    f"The visitor can now access: {', '.join([s['name'] for s in newly_consensus_approved_sections])}"
                )
            elif new_status == 'rejected':
                response_data['message'] = "Visitor request has been rejected. Access denied for all sections."
            elif progress.get('sections_partially_approved', 0) > 0:
                response_data['message'] = (
                    f"Your response recorded. {progress['sections_partially_approved']} section(s) have one approval and need the other approver's approval. "
                    f"Sections need BOTH approvers to approve for access to be granted."
                )
            else:
                response_data['message'] = (
                    f"Your response recorded. Waiting for other approver(s) to respond. "
                    f"Both approvers must approve each section."
                )
            
            return Response(response_data)
            
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error in VisitorSectionApprovalView: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
        
#         # NEW: Check if site is in cooldown
#         if visitor.site and visitor.site.is_on_cooldown():
#             cooldown = visitor.site.get_active_cooldown()
#             return Response(
#                 {'error': f'Cannot check in. {cooldown.get_active_message()}'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # NEW: Check site daily capacity
#         if visitor.site and not visitor.site.is_capacity_available():
#             return Response(
#                 {'error': f'Daily visitor limit reached for {visitor.site.name}. Please try tomorrow.'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # NEW: Check if visitor has at least one approved section
#         approved_sections_count = visitor.visitor_section_approvals.filter(status='approved').count()
#         if approved_sections_count == 0:
#             return Response(
#                 {'error': 'Visitor has no approved sections. Cannot check in.'},
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
            
#             # Get access matrix for security
#             access_matrix = visitor.get_access_matrix()
            
#             return Response({
#                 'message': f'Visitor checked in successfully{result["timing_message"]}',
#                 'check_in_time': result['check_in_time'],
#                 'designated_check_in_time': visitor.designated_check_in,
#                 'early_arrival_minutes': result['early_arrival_minutes'],
#                 'late_arrival_minutes': result['late_arrival_minutes'],
#                 'site': visitor.site.name if visitor.site else None,
#                 'site_capacity_remaining': visitor.site.daily_capacity_limit - visitor.site.get_today_visitor_count() if visitor.site else None,
#                 'access_matrix': access_matrix,
#                 'approved_sections_summary': {
#                     'total_approved': len([a for a in access_matrix if a['status'] == 'approved']),
#                     'requires_escort': [a['section'] for a in access_matrix if a['status'] == 'approved' and a['requires_escort']]
#                 }
#             })
#         except ValueError as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
        
#         # Check if site is in cooldown
#         if visitor.site and hasattr(visitor.site, 'is_on_cooldown') and visitor.site.is_on_cooldown():
#             cooldown = visitor.site.get_active_cooldown()
#             return Response(
#                 {'error': f'Cannot check in. {cooldown.get_active_message()}'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Check site daily capacity
#         if visitor.site and hasattr(visitor.site, 'is_capacity_available') and not visitor.site.is_capacity_available():
#             return Response(
#                 {'error': f'Daily visitor limit reached for {visitor.site.name}. Please try tomorrow.'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # CRITICAL: Check if visitor has consensus-approved sections (both approvers approved)
#         can_check_in, message = visitor.can_check_in()
#         if not can_check_in:
#             return Response({'error': message}, status=status.HTTP_403_FORBIDDEN)
        
#         if visitor.status != 'approved':
#             return Response(
#                 {'error': f'Visitor status is {visitor.status}, not approved for check-in'},
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
            
#             # Get access matrix with consensus info
#             access_matrix = visitor.get_access_matrix()
#             accessible_sections = [s for s in access_matrix if s.get('is_accessible', False)]
#             consensus_approved_sections = visitor.get_consensus_approved_sections()
            
#             return Response({
#                 'message': f'Visitor checked in successfully{result["timing_message"]}',
#                 'check_in_time': result['check_in_time'],
#                 'designated_check_in_time': visitor.designated_check_in,
#                 'early_arrival_minutes': result['early_arrival_minutes'],
#                 'late_arrival_minutes': result['late_arrival_minutes'],
#                 'site': visitor.site.name if visitor.site else None,
#                 'site_capacity_remaining': visitor.site.daily_capacity_limit - visitor.site.get_today_visitor_count() if visitor.site else None,
#                 'access_matrix': access_matrix,
#                 'accessible_sections': [
#                     {
#                         'section_id': s['section_id'],
#                         'section_name': s['section_name'],
#                         'requires_escort': s['requires_escort'],
#                         'location': s['location'],
#                         'site': s['site']
#                     }
#                     for s in accessible_sections
#                 ],
#                 'consensus_summary': {
#                     'total_sections_requested': visitor.requested_sections.count(),
#                     'accessible_sections_count': len(accessible_sections),
#                     'requires_escort': [s['section_name'] for s in accessible_sections if s['requires_escort']],
#                     'approval_mode': 'consensus_based (both approvers required)',
#                     'access_granted_message': f"Access granted to {len(accessible_sections)} section(s). Only sections approved by BOTH approvers are accessible."
#                 }
#             })
#         except ValueError as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# class VisitorCheckInView(APIView):
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, pk):
#         visitor = get_object_or_404(Visitor, pk=pk)
        
#         # Check permission
#         # this needs to be handled afterwards
#         # if not (request.user.is_superuser or visitor.created_by == request.user):
#         #     return Response(
#         #         {'error': 'You do not have permission to check-in this visitor'},
#         #         status=status.HTTP_403_FORBIDDEN
#         #     )
        
#         # Check if site is in cooldown
#         if visitor.site and hasattr(visitor.site, 'is_on_cooldown') and visitor.site.is_on_cooldown():
#             cooldown = visitor.site.get_active_cooldown()
#             return Response(
#                 {'error': f'Cannot check in. {cooldown.get_active_message()}'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Check site daily capacity
#         if visitor.site and hasattr(visitor.site, 'is_capacity_available') and not visitor.site.is_capacity_available():
#             return Response(
#                 {'error': f'Daily visitor limit reached for {visitor.site.name}. Please try tomorrow.'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # CRITICAL: Check if visitor has consensus-approved sections (both approvers approved)
#         can_check_in, message = visitor.can_check_in()
#         if not can_check_in:
#             return Response({'error': message}, status=status.HTTP_403_FORBIDDEN)
        
#         if visitor.status != 'approved':
#             return Response(
#                 {'error': f'Visitor status is {visitor.status}, not approved for check-in'},
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
            
#             # NEW: Auto-create section tracking records for approved sections (consensus approved)
#             from account.models import VisitorSectionTracking
#             approved_sections = visitor.get_consensus_approved_sections()
            
#             # Get access matrix with consensus info
#             access_matrix = visitor.get_access_matrix()
#             accessible_sections = [s for s in access_matrix if s.get('is_accessible', False)]
#             consensus_approved_sections = visitor.get_consensus_approved_sections()
            
#             # Get section tracking summary
#             section_trackings = visitor.section_trackings.all()
#             section_tracking_summary = {
#                 'total_sections': section_trackings.count(),
#                 'not_started': section_trackings.filter(status='pending').count(),
#                 'in_progress': section_trackings.filter(status='in_progress').count(),
#                 'completed': section_trackings.filter(status='completed').count()
#                 # 'tracking_created_count': tracking_created_count
#             }
            
#             return Response({
#                 'message': f'Visitor checked in successfully{result["timing_message"]}',
#                 'check_in_time': result['check_in_time'],
#                 'designated_check_in_time': visitor.designated_check_in,
#                 'early_arrival_minutes': result['early_arrival_minutes'],
#                 'late_arrival_minutes': result['late_arrival_minutes'],
#                 'site': visitor.site.name if visitor.site else None,
#                 'site_capacity_remaining': visitor.site.daily_capacity_limit - visitor.site.get_today_visitor_count() if visitor.site else None,
#                 'access_matrix': access_matrix,
#                 'accessible_sections': [
#                     {
#                         'section_id': s['section_id'],
#                         'section_name': s['section_name'],
#                         'requires_escort': s['requires_escort'],
#                         'location': s['location'],
#                         'site': s['site']
#                     }
#                     for s in accessible_sections
#                 ],
#                 'consensus_summary': {
#                     'total_sections_requested': visitor.requested_sections.count(),
#                     'accessible_sections_count': len(accessible_sections),
#                     'requires_escort': [s['section_name'] for s in accessible_sections if s['requires_escort']],
#                     'approval_mode': 'consensus_based (both approvers required)',
#                     'access_granted_message': f"Access granted to {len(accessible_sections)} section(s). Only sections approved by BOTH approvers are accessible."
#                 },
#                 'section_tracking_summary': section_tracking_summary
#             })
#         except ValueError as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# class VisitorCheckOutView(APIView):
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, pk):
#         visitor = get_object_or_404(Visitor, pk=pk)
        
#         # Check permission
#         # if not (request.user.is_superuser or visitor.created_by == request.user):
#         #     return Response(
#         #         {'error': 'You do not have permission to check-out this visitor'},
#         #         status=status.HTTP_403_FORBIDDEN
#         #     )
        
#         if not visitor.actual_check_in:
#             return Response(
#                 {'error': 'Visitor must check in first'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         if visitor.actual_check_out:
#             return Response(
#                 {'error': f'Visitor already checked out at {visitor.actual_check_out}'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         serializer = VisitorCheckOutSerializer(data=request.data)
#         notes = serializer.initial_data.get('notes') if serializer.is_valid() else None
        
#         try:
#             result = visitor.check_out(notes=notes)
#             response_data = {
#                 'message': 'Visitor checked out successfully',
#                 'check_out_time': result['check_out_time'],
#                 'visit_duration_minutes': result['visit_duration_minutes'],
#                 'designated_check_out_time': visitor.designated_check_out,
#             }
            
#             if 'overtime_minutes' in result:
#                 response_data['message'] = result['message']
#                 response_data['overtime_minutes'] = result['overtime_minutes']
            
#             return Response(response_data)
#         except ValueError as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class VisitorCheckInView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request, pk):
        visitor = get_object_or_404(Visitor, pk=pk)
        
        # Check if site is in cooldown
        if visitor.site and hasattr(visitor.site, 'is_on_cooldown') and visitor.site.is_on_cooldown():
            cooldown = visitor.site.get_active_cooldown()
            return Response(
                {'error': f'Cannot check in. {cooldown.get_active_message()}'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check site daily capacity
        if visitor.site and hasattr(visitor.site, 'is_capacity_available') and not visitor.site.is_capacity_available():
            return Response(
                {'error': f'Daily visitor limit reached for {visitor.site.name}. Please try tomorrow.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if visitor has consensus-approved sections (both approvers approved)
        can_check_in, message = visitor.can_check_in()
        if not can_check_in:
            return Response({'error': message}, status=status.HTTP_403_FORBIDDEN)
        
        if visitor.status not in ('approved','partially_approved'):
            return Response(
                {'error': f'Visitor status is {visitor.status}, not approved for check-in'},
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
            
            # Get access matrix with consensus info
            access_matrix = visitor.get_access_matrix()
            accessible_sections = [s for s in access_matrix if s.get('is_accessible', False)]
            
            return Response({
                'success': True,
                'message': f'Visitor checked in successfully{result["timing_message"]}',
                'check_in_time': result['check_in_time'],
                'designated_check_in_time': visitor.designated_check_in,
                'early_arrival_minutes': result['early_arrival_minutes'],
                'late_arrival_minutes': result['late_arrival_minutes'],
                'site': visitor.site.name if visitor.site else None,
                'site_capacity_remaining': visitor.site.daily_capacity_limit - visitor.site.get_today_visitor_count() if visitor.site else None,
                'access_matrix': access_matrix,
                'accessible_sections': [
                    {
                        'section_id': s['section_id'],
                        'section_name': s['section_name'],
                        'requires_escort': s['requires_escort'],
                        'location': s['location'],
                        'site': s['site']
                    }
                    for s in accessible_sections
                ],
                'consensus_summary': {
                    'total_sections_requested': visitor.requested_sections.count(),
                    'accessible_sections_count': len(accessible_sections),
                    'requires_escort': [s['section_name'] for s in accessible_sections if s['requires_escort']],
                    'approval_mode': 'consensus_based (both approvers required)',
                    'access_granted_message': f"Access granted to {len(accessible_sections)} section(s). Only sections approved by BOTH approvers are accessible."
                }
            })
        except ValueError as e:
            print(str(e))
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        


class VisitorCheckOutView(APIView):
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request, pk):
        visitor = get_object_or_404(Visitor, pk=pk)
        
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
        
        # CRITICAL FIX: Check if visitor has any active section check-ins
        can_checkout, message = visitor.can_check_out_site()
        if not can_checkout:
            return Response(
                {'error': message, 'active_sections': [
                    {
                        'section_id': s.section.id,
                        'section_name': s.section.name,
                        'check_in_time': s.section_check_in
                    }
                    for s in visitor.get_active_sections()
                ]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VisitorCheckOutSerializer(data=request.data)
        notes = serializer.initial_data.get('notes') if serializer.is_valid() else None
        
        try:
            result = visitor.check_out(notes=notes)
            response_data = {
                'success': True,
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



# views.py - Add this new view

# class MyPendingSectionApprovalsView(APIView):
#     """Get all sections pending approval for the current logged-in approver"""
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def get(self, request):
#         # Get all pending section approvals for this approver
#         pending_approvals = VisitorSectionApproval.objects.filter(
#             approver=request.user,
#             status='pending'
#         ).select_related('visitor', 'section', 'section__location', 'section__location__site')
        
#         # Group by visitor
#         visitors_data = {}
#         for approval in pending_approvals:
#             visitor = approval.visitor
#             if visitor.id not in visitors_data:
#                 # Get progress for this visitor
#                 total_for_me = visitor.visitor_section_approvals.filter(approver=request.user).count()
#                 approved_for_me = visitor.visitor_section_approvals.filter(
#                     approver=request.user, 
#                     status='approved'
#                 ).count()

                
                
#                 # Get other approver's progress
#                 other_approver = visitor.selected_approvers.exclude(id=request.user.id).first()
#                 other_approved = 0
#                 if other_approver:
#                     other_approved = visitor.visitor_section_approvals.filter(
#                         approver=other_approver,
#                         status='approved'
#                     ).count()
                
#                 visitors_data[visitor.id] = {
#                     'visitor': visitor,
#                     'total_sections_for_me': total_for_me,
#                     'approved_sections_for_me': approved_for_me,
#                     'other_approver_approved_count': other_approved,
#                     'other_approver_name': other_approver.full_name if other_approver else None,
#                     'pending_sections': []
#                 }
#             visitors_data[visitor.id]['pending_sections'].append(approval.section)
        
#         # Format response
#         result = []
#         for data in visitors_data.values():
#             visitor = data['visitor']
#             result.append({
#                 'visitor_id': visitor.id,
#                 'visitor_name': visitor.full_name,
#                 'visitor_email': visitor.email,
#                 'visitor_phone': visitor.phone_number,
#                 'company_name': visitor.company_name,
#                 'purpose_of_visit': visitor.purpose_of_visit,
#                 'designated_check_in': visitor.designated_check_in,
#                 'designated_check_out': visitor.designated_check_out,
#                 'site_name': visitor.site.name if visitor.site else None,
#                 'created_by': visitor.created_by.full_name,
#                 'created_at': visitor.created_at,
#                 'overall_status': visitor.status,
#                 'approval_mode': 'consensus_based',
#                 'consensus_rule': 'Section accessible only if BOTH approvers approve it',
#                 'my_progress': {
#                     'total_sections': data['total_sections_for_me'],
#                     'approved': data['approved_sections_for_me'],
#                     'pending': len(data['pending_sections']),
#                     'completed': len(data['pending_sections']) == 0
#                 },
#                 'other_approver': {
#                     'name': data['other_approver_name'],
#                     'approved_count': data['other_approver_approved_count']
#                 },
#                 'pending_sections': [
#                     {
#                         'id': section.id,
#                         'name': section.name,
#                         'code': section.code,
#                         'location': section.location.name if section.location else None,
#                         'site': section.location.site.name if section.location and section.location.site else None,
#                         'section_type': section.section_type,
#                         'requires_escort': section.requires_escort,
#                         'daily_capacity': section.daily_capacity
#                     }
#                     for section in data['pending_sections']
#                 ]
#             })
        
#         return Response({
#             'total_pending_visitors': len(result),
#             'total_pending_approvals': pending_approvals.count(),
#             'pending_approvals': result
#         })

class MyPendingSectionApprovalsView(APIView):
    """Get all sections pending approval for the current logged-in approver"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        # Get all pending section approvals for this approver
        pending_approvals = VisitorSectionApproval.objects.filter(
            approver=request.user,
            status='pending'
        ).select_related('visitor', 'section', 'section__location', 'section__location__site')
        
        # Group by visitor
        visitors_data = {}
        for approval in pending_approvals:
            visitor = approval.visitor
            if visitor.id not in visitors_data:
                # Get progress for this visitor
                total_for_me = visitor.visitor_section_approvals.filter(approver=request.user).count()
                approved_for_me = visitor.visitor_section_approvals.filter(
                    approver=request.user, 
                    status='approved'
                ).count()
                
                # Get other approver's progress
                other_approver = visitor.selected_approvers.exclude(id=request.user.id).first()
                other_approved = 0
                if other_approver:
                    other_approved = visitor.visitor_section_approvals.filter(
                        approver=other_approver,
                        status='approved'
                    ).count()
                
                # Get photo URL - handle both URL and FileField
                photo_url = None
                if hasattr(visitor, 'photo') and visitor.photo:
                    if isinstance(visitor.photo, str):
                        # If it's a URL string
                        photo_url = visitor.photo
                    elif hasattr(visitor.photo, 'url'):
                        # If it's a FileField or ImageField
                        photo_url = visitor.photo.url
                
                visitors_data[visitor.id] = {
                    'visitor': visitor,
                    'total_sections_for_me': total_for_me,
                    'approved_sections_for_me': approved_for_me,
                    'other_approver_approved_count': other_approved,
                    'other_approver_name': other_approver.full_name if other_approver else None,
                    'pending_sections': [],
                    'photo_url': photo_url
                }
            visitors_data[visitor.id]['pending_sections'].append(approval.section)
        
        # Format response
        result = []
        for data in visitors_data.values():
            visitor = data['visitor']
            result.append({
                'visitor_id': visitor.id,
                'visitor_name': visitor.full_name,
                'visitor_email': visitor.email,
                'visitor_phone': visitor.phone_number,
                'visitor_photo': data['photo_url'],  # Added visitor photo
                'company_name': visitor.company_name,
                'purpose_of_visit': visitor.purpose_of_visit,
                'designated_check_in': visitor.designated_check_in,
                'designated_check_out': visitor.designated_check_out,
                'site_name': visitor.site.name if visitor.site else None,
                'site_id': visitor.site.id if visitor.site else None,
                'created_by': visitor.created_by.full_name,
                'created_by_id': visitor.created_by.id,
                'created_at': visitor.created_at,
                'overall_status': visitor.status,
                'approval_mode': 'consensus_based',
                'consensus_rule': 'Section accessible only if BOTH approvers approve it',
                'my_progress': {
                    'total_sections': data['total_sections_for_me'],
                    'approved': data['approved_sections_for_me'],
                    'pending': len(data['pending_sections']),
                    'completed': len(data['pending_sections']) == 0
                },
                'other_approver': {
                    'name': data['other_approver_name'],
                    'approved_count': data['other_approver_approved_count']
                },
                'pending_sections': [
                    {
                        'id': section.id,
                        'name': section.name,
                        'code': section.code,
                        'location': section.location.name if section.location else None,
                        'location_id': section.location.id if section.location else None,
                        'site': section.location.site.name if section.location and section.location.site else None,
                        'site_id': section.location.site.id if section.location and section.location.site else None,
                        'section_type': section.section_type,
                        'requires_escort': section.requires_escort,
                        'daily_capacity': section.daily_capacity,
                        'current_occupancy': section.get_current_occupancy() if hasattr(section, 'get_current_occupancy') else 0
                    }
                    for section in data['pending_sections']
                ]
            })
        
        return Response({
            'total_pending_visitors': len(result),
            'total_pending_approvals': pending_approvals.count(),
            'pending_approvals': result
        })

class VisitorSectionTrackingView(APIView):
    """Get all section tracking information for a visitor"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, visitor_id):
        visitor = get_object_or_404(Visitor, pk=visitor_id)
        
        # Check permission
        if not (request.user.is_superuser or 
                visitor.created_by == request.user or
                visitor.selected_approvers.filter(id=request.user.id).exists() or
                request.user.department.lower() in ['security', 'safety']):
            return Response(
                {'error': 'You do not have permission to view section tracking'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        section_trackings = VisitorSectionTracking.objects.filter(visitor=visitor)
        serializer = VisitorSectionTrackingSerializer(section_trackings, many=True)
        
        # Calculate summary statistics
        total_sections = section_trackings.count()
        completed_sections = section_trackings.filter(status='completed').count()
        in_progress_sections = section_trackings.filter(status='in_progress').count()
        pending_sections = section_trackings.filter(status='pending').count()
        total_duration = sum([st.duration_minutes for st in section_trackings])
        
        return Response({
            'visitor': {
                'id': visitor.id,
                'full_name': visitor.full_name,
                'email': visitor.email,
                'phone_number': visitor.phone_number,
                'status': visitor.status,
                'designated_check_in': visitor.designated_check_in,
                'designated_check_out': visitor.designated_check_out,
            },
            'section_trackings': serializer.data,
            'summary': {
                'total_sections': total_sections,
                'completed_sections': completed_sections,
                'in_progress_sections': in_progress_sections,
                'pending_sections': pending_sections,
                'total_duration_minutes': total_duration,
                'total_duration_hours': round(total_duration / 60, 2),
                'completion_percentage': round((completed_sections / total_sections) * 100, 2) if total_sections > 0 else 0
            }
        })


# class VisitorSectionCheckInView(APIView):
#     """Security personnel checks visitor into a specific section"""
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, visitor_id):
#         visitor = get_object_or_404(Visitor, pk=visitor_id)
        
#         # Check if user is security personnel or superadmin
#         # if not (request.user.is_superuser or 
#         #         request.user.department.lower() in ['security', 'safety']):
#         #     return Response(
#         #         {'error': 'Only security personnel can perform section check-in'},
#         #         status=status.HTTP_403_FORBIDDEN
#         #     )
#         from .serializers import SectionCheckInSerializer
#         serializer = SectionCheckInSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
#         section_id = serializer.validated_data['section_id']
#         notes = serializer.validated_data.get('notes', '')
        
#         # Get the section
#         try:
#             section = Section.objects.get(id=section_id, is_active=True)
#         except Section.DoesNotExist:
#             return Response({'error': 'Section not found'}, status=status.HTTP_404_NOT_FOUND)
        
#         # Check if visitor has access to this section (approved by both approvers)
#         if not visitor.has_section_access(section):
#             return Response(
#                 {'error': f'Visitor does not have access to {section.name}. This section needs approval from both approvers.'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         # Check if visitor is checked in overall to the site
#         if visitor.status != 'checked_in':
#             return Response(
#                 {'error': 'Visitor must be checked in to the site first before accessing sections'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Get or create section tracking record
#         section_tracking, created = VisitorSectionTracking.objects.get_or_create(
#             visitor=visitor,
#             section=section
#         )
        
#         # Check if already checked in (and not checked out)
#         if section_tracking.section_check_in and not section_tracking.section_check_out:
#             return Response(
#                 {'error': f'Visitor is already checked in to {section.name} since {section_tracking.section_check_in.strftime("%I:%M %p")}'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Check if already completed
#         if section_tracking.status == 'completed':
#             return Response(
#                 {'error': f'Visitor has already completed their visit to {section.name}'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Perform section check-in
#         section_tracking.section_check_in = timezone.now()
#         section_tracking.check_in_notes = notes
#         section_tracking.checked_in_by = request.user
#         section_tracking.save()  # Auto-updates status to 'in_progress'
        
#         # Send WebSocket notification to creator and approvers
#         from notification.utils import send_websocket_notification
        
#         notification_data = {
#             'visitor_id': visitor.id,
#             'visitor_name': visitor.full_name,
#             'section_id': section.id,
#             'section_name': section.name,
#             'check_in_time': section_tracking.section_check_in.isoformat(),
#             'checked_in_by': request.user.full_name,
#             'message': f'🔵 {visitor.full_name} entered {section.name} at {section_tracking.section_check_in.strftime("%I:%M %p")}'
#         }
        
#         # Notify creator
#         send_websocket_notification(
#             user_id=visitor.created_by.id,
#             notification_type='section_checkin',
#             data=notification_data
#         )
        
#         # Notify all approvers
#         for approver in visitor.selected_approvers.all():
#             send_websocket_notification(
#                 user_id=approver.id,
#                 notification_type='section_checkin',
#                 data=notification_data
#             )
        
#         return Response({
#             'message': f'✅ Successfully checked in {visitor.full_name} to {section.name}',
#             'section_check_in': section_tracking.section_check_in,
#             'section_name': section.name,
#             'status': section_tracking.status,
#             'check_in_time_formatted': section_tracking.section_check_in.strftime("%I:%M %p on %B %d, %Y")
#         })


# class VisitorSectionCheckOutView(APIView):
#     """Security personnel checks visitor out of a specific section"""
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def post(self, request, visitor_id):
#         visitor = get_object_or_404(Visitor, pk=visitor_id)
        
#         # Check if user is security personnel or superadmin
#         # if not (request.user.is_superuser or 
#         #         request.user.department.lower() in ['security', 'safety']):
#         #     return Response(
#         #         {'error': 'Only security personnel can perform section check-out'},
#         #         status=status.HTTP_403_FORBIDDEN
#         #     )
#         from .serializers import SectionCheckOutSerializer
#         serializer = SectionCheckOutSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
#         section_id = serializer.validated_data['section_id']
#         notes = serializer.validated_data.get('notes', '')
        
#         try:
#             section_tracking = VisitorSectionTracking.objects.get(
#                 visitor=visitor,
#                 section_id=section_id
#             )
#         except VisitorSectionTracking.DoesNotExist:
#             return Response(
#                 {'error': 'Visitor has not checked in to this section'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Check if already checked out
#         if section_tracking.section_check_out:
#             return Response(
#                 {'error': f'Visitor already checked out of {section_tracking.section.name} at {section_tracking.section_check_out.strftime("%I:%M %p")}'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Check if checked in
#         if not section_tracking.section_check_in:
#             return Response(
#                 {'error': 'Visitor has not checked in to this section yet. Please check them in first.'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Perform section check-out
#         section_tracking.section_check_out = timezone.now()
#         section_tracking.check_out_notes = notes
#         section_tracking.checked_out_by = request.user
#         section_tracking.save()  # Auto-updates status and duration
        
#         # Send WebSocket notification
#         from notification.utils import send_websocket_notification
        
#         notification_data = {
#             'visitor_id': visitor.id,
#             'visitor_name': visitor.full_name,
#             'section_id': section_tracking.section.id,
#             'section_name': section_tracking.section.name,
#             'check_in_time': section_tracking.section_check_in.isoformat(),
#             'check_out_time': section_tracking.section_check_out.isoformat(),
#             'duration_minutes': section_tracking.duration_minutes,
#             'checked_out_by': request.user.full_name,
#             'message': f'🟢 {visitor.full_name} exited {section_tracking.section.name} after {section_tracking.duration_minutes} minutes'
#         }
        
#         # Notify creator
#         send_websocket_notification(
#             user_id=visitor.created_by.id,
#             notification_type='section_checkout',
#             data=notification_data
#         )
        
#         # Notify all approvers
#         for approver in visitor.selected_approvers.all():
#             send_websocket_notification(
#                 user_id=approver.id,
#                 notification_type='section_checkout',
#                 data=notification_data
#             )
        
#         return Response({
#             'message': f'✅ Successfully checked out {visitor.full_name} from {section_tracking.section.name}',
#             'section_check_out': section_tracking.section_check_out,
#             'duration_minutes': section_tracking.duration_minutes,
#             'duration_formatted': f'{section_tracking.duration_minutes} minutes ({round(section_tracking.duration_minutes / 60, 1)} hours)',
#             'section_name': section_tracking.section.name,
#             'status': section_tracking.status
#         })


class VisitorSectionCheckInView(APIView):
    """Security personnel checks visitor into a specific section"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request, visitor_id):
        visitor = get_object_or_404(Visitor, pk=visitor_id)
        
        from .serializers import SectionCheckInSerializer
        serializer = SectionCheckInSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        section_id = serializer.validated_data['section_id']
        notes = serializer.validated_data.get('notes', '')
        
        # Get the section
        try:
            section = Section.objects.get(id=section_id, is_active=True)
        except Section.DoesNotExist:
            return Response({'error': 'Section not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if visitor has access to this section (approved by both approvers)
        if not visitor.has_section_access(section):
            return Response(
                {'error': f'Visitor does not have access to {section.name}. This section needs approval from both approvers.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if visitor is checked in overall to the site
        if visitor.status != 'checked_in':
            return Response(
                {'error': 'Visitor must be checked in to the site first before accessing sections'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create section tracking record
        section_tracking, created = VisitorSectionTracking.objects.get_or_create(
            visitor=visitor,
            section=section
        )
        
        # Check if already checked in (and not checked out)
        if section_tracking.section_check_in and not section_tracking.section_check_out:
            return Response(
                {'error': f'Visitor is already checked in to {section.name} since {section_tracking.section_check_in.strftime("%I:%M %p")}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already completed
        if section_tracking.status == 'completed':
            return Response(
                {'error': f'Visitor has already completed their visit to {section.name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform section check-in
        section_tracking.section_check_in = timezone.now()
        section_tracking.check_in_notes = notes
        section_tracking.checked_in_by = request.user
        section_tracking.save()  # Auto-updates status to 'in_progress'
        
        # Send WebSocket notification
        from notification.utils import send_websocket_notification
        
        notification_data = {
            'visitor_id': visitor.id,
            'visitor_name': visitor.full_name,
            'section_id': section.id,
            'section_name': section.name,
            'check_in_time': section_tracking.section_check_in.isoformat(),
            'checked_in_by': request.user.full_name,
            'message': f'🔵 {visitor.full_name} entered {section.name} at {section_tracking.section_check_in.strftime("%I:%M %p")}'
        }
        
        # Notify creator and approvers
        send_websocket_notification(
            user_id=visitor.created_by.id,
            notification_type='section_checkin',
            data=notification_data
        )
        
        for approver in visitor.selected_approvers.all():
            send_websocket_notification(
                user_id=approver.id,
                notification_type='section_checkin',
                data=notification_data
            )
        
        return Response({
            'success': True,
            'message': f'✅ Successfully checked in {visitor.full_name} to {section.name}',
            'section_check_in': section_tracking.section_check_in,
            'section_name': section.name,
            'status': section_tracking.status,
            'check_in_time_formatted': section_tracking.section_check_in.strftime("%I:%M %p on %B %d, %Y")
        })
    


class VisitorSectionCheckOutView(APIView):
    """Security personnel checks visitor out of a specific section"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request, visitor_id):
        visitor = get_object_or_404(Visitor, pk=visitor_id)
        
        from .serializers import SectionCheckOutSerializer
        serializer = SectionCheckOutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        section_id = serializer.validated_data['section_id']
        notes = serializer.validated_data.get('notes', '')
        
        try:
            section_tracking = VisitorSectionTracking.objects.get(
                visitor=visitor,
                section_id=section_id
            )
        except VisitorSectionTracking.DoesNotExist:
            return Response(
                {'error': 'Visitor has not checked in to this section'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already checked out
        if section_tracking.section_check_out:
            return Response(
                {'error': f'Visitor already checked out of {section_tracking.section.name} at {section_tracking.section_check_out.strftime("%I:%M %p")}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if checked in
        if not section_tracking.section_check_in:
            return Response(
                {'error': 'Visitor has not checked in to this section yet. Please check them in first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform section check-out
        section_tracking.section_check_out = timezone.now()
        section_tracking.check_out_notes = notes
        section_tracking.checked_out_by = request.user
        section_tracking.save()  # Auto-updates status and duration
        
        # Send WebSocket notification
        from notification.utils import send_websocket_notification
        
        notification_data = {
            'visitor_id': visitor.id,
            'visitor_name': visitor.full_name,
            'section_id': section_tracking.section.id,
            'section_name': section_tracking.section.name,
            'check_in_time': section_tracking.section_check_in.isoformat(),
            'check_out_time': section_tracking.section_check_out.isoformat(),
            'duration_minutes': section_tracking.duration_minutes,
            'checked_out_by': request.user.full_name,
            'message': f'🟢 {visitor.full_name} exited {section_tracking.section.name} after {section_tracking.duration_minutes} minutes'
        }
        
        # Notify creator and approvers
        send_websocket_notification(
            user_id=visitor.created_by.id,
            notification_type='section_checkout',
            data=notification_data
        )
        
        for approver in visitor.selected_approvers.all():
            send_websocket_notification(
                user_id=approver.id,
                notification_type='section_checkout',
                data=notification_data
            )
        
        return Response({
            'success': True,
            'message': f'✅ Successfully checked out {visitor.full_name} from {section_tracking.section.name}',
            'section_check_out': section_tracking.section_check_out,
            'duration_minutes': section_tracking.duration_minutes,
            'duration_formatted': f'{section_tracking.duration_minutes} minutes ({round(section_tracking.duration_minutes / 60, 1)} hours)',
            'section_name': section_tracking.section.name,
            'status': section_tracking.status
        })


class VisitorCompleteProfileView(APIView):
    """Get complete visitor profile including section tracking for the profile page"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, visitor_id):
        visitor = get_object_or_404(Visitor, pk=visitor_id)
        
        # Check permission
        if not (request.user.is_superuser or 
                visitor.created_by == request.user or
                visitor.selected_approvers.filter(id=request.user.id).exists() or
                request.user.department.lower() in ['security', 'safety']):
            return Response(
                {'error': 'You do not have permission to view this visitor profile'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Use the extended serializer
        from .serializers import VisitorWithSectionsSerializer

        serializer = VisitorWithSectionsSerializer(visitor)
        
        # Add section tracking summary
        section_trackings = visitor.section_trackings.all()
        total_duration = sum([st.duration_minutes for st in section_trackings])
        
        response_data = serializer.data
        response_data['section_tracking_summary'] = {
            'total_sections_visited': section_trackings.filter(status='completed').count(),
            'total_time_spent_minutes': total_duration,
            'total_time_spent_formatted': f'{total_duration} minutes ({round(total_duration / 60, 1)} hours)',
            'current_section': next(
                (st.section.name for st in section_trackings if st.status == 'in_progress'), 
                None
            )
        }
        
        return Response(response_data)


class AutoCreateSectionTrackingView(APIView):
    """Auto-create section tracking records when visitor is approved"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request, visitor_id):
        visitor = get_object_or_404(Visitor, pk=visitor_id)
        
        if not request.user.is_superuser:
            return Response({'error': 'Only superadmin can trigger this'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all approved sections for this visitor
        approved_sections = visitor.get_consensus_approved_sections()
        
        created_count = 0
        for section in approved_sections:
            _, created = VisitorSectionTracking.objects.get_or_create(
                visitor=visitor,
                section=section
            )
            if created:
                created_count += 1
        
        return Response({
            'message': f'Created {created_count} section tracking records',
            'total_approved_sections': len(approved_sections)
        })



# account/views.py

from account.excel_utils import ExcelExportUtil
import io
from datetime import datetime
from django.http import HttpResponse
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

# Import your models
from account.models import Visitor
from account.permissions import IsEmployee
from account.excel_utils import ExcelExportUtil

# class ExportVisitorsToExcelView(APIView):
#     """Export visitors data to Excel file with date range filtering"""
#     permission_classes = [IsAuthenticated, IsEmployee]
    
#     def get(self, request):
#         # Get date range parameters
#         start_date = request.query_params.get('start_date')
#         end_date = request.query_params.get('end_date')
#         status_filter = request.query_params.get('status', '')
        
#         # Validate date range
#         if not start_date or not end_date:
#             return Response({
#                 'error': 'Both start_date and end_date are required. Format: YYYY-MM-DD'
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
#             end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
#         except ValueError:
#             return Response({
#                 'error': 'Invalid date format. Use YYYY-MM-DD'
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         # Filter visitors by date range
#         user = request.user
#         visitors = Visitor.objects.filter(
#             models.Q(created_at__date__gte=start_date_obj.date()) &
#             models.Q(created_at__date__lte=end_date_obj.date())
#         )
        
#         # Apply status filter if provided
#         if status_filter:
#             visitors = visitors.filter(status=status_filter)
        
#         # Apply user permissions
#         if not user.is_superuser:
#             visitors = visitors.filter(
#                 models.Q(created_by=user) | 
#                 models.Q(selected_approvers=user)
#             ).distinct()
        
#         # Order by created date
#         visitors = visitors.order_by('-created_at')
        
#         # Check if any visitors found
#         if not visitors.exists():
#             return Response({
#                 'warning': f'No visitors found for date range {start_date} to {end_date}'
#             }, status=status.HTTP_404_NOT_FOUND)
        
#         # Generate Excel using utility class
#         excel_util = ExcelExportUtil(visitors, start_date, end_date, status_filter)
#         workbook = excel_util.generate()
        
#         # Save to BytesIO
#         output = io.BytesIO()
#         workbook.save(output)
#         output.seek(0)
        
#         # Generate filename
#         filename = f"visitors_export_{start_date}_to_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
#         # Return Excel file
#         response = HttpResponse(
#             output.getvalue(),
#             content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         )
#         response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
#         return response
    

class ExportVisitorsToExcelView(APIView):
    """Export visitors data to Excel file with date range filtering"""
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        # Get date range parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status', '')
        
        # Validate date range
        if not start_date or not end_date:
            return Response({
                'error': 'Both start_date and end_date are required. Format: YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return Response({
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter visitors by designated_check_in date range (FIXED)
        user = request.user
        
        # Debug: Print user info
        print(f"User: {user.email}, is_superuser: {user.is_superuser}")
        print(f"Date range: {start_date} to {end_date}")
        
        # Filter by designated_check_in date range
        visitors = Visitor.objects.filter(
            designated_check_in__date__gte=start_date_obj.date(),
            designated_check_in__date__lte=end_date_obj.date()
        )
        
        # Debug: Print count before permission filter
        print(f"Visitors found before permission filter: {visitors.count()}")
        for v in visitors:
            print(f"Visitor: {v.full_name}, designated_check_in: {v.designated_check_in}, status: {v.status}")
        
        # Apply status filter if provided and not 'all'
        if status_filter and status_filter != 'all':
            visitors = visitors.filter(status=status_filter)
            print(f"After status filter ({status_filter}): {visitors.count()}")
        
        # Apply user permissions
        if not user.is_superuser:
            visitors = visitors.filter(
                models.Q(created_by=user) | 
                models.Q(selected_approvers=user)
            ).distinct()
            print(f"After permission filter: {visitors.count()}")
        
        # Order by created date
        visitors = visitors.order_by('-created_at')
        
        # Check if any visitors found
        if not visitors.exists():
            # Debug: Show what visitors exist in DB
            all_visitors = Visitor.objects.all()
            print(f"Total visitors in DB: {all_visitors.count()}")
            
            return Response({
                'warning': f'No visitors found for date range {start_date} to {end_date}',
                'debug_info': {
                    'total_visitors_in_db': all_visitors.count(),
                    'user_email': user.email,
                    'is_superuser': user.is_superuser,
                    'status_filter': status_filter,
                    'date_range': f"{start_date} to {end_date}",
                    'sample_visitors': [
                        {
                            'name': v.full_name,
                            'designated_check_in': str(v.designated_check_in),
                            'status': v.status,
                            'created_by': str(v.created_by.email)
                        } for v in all_visitors[:5]
                    ]
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Generate Excel using utility class
        excel_util = ExcelExportUtil(visitors, start_date, end_date, status_filter)
        workbook = excel_util.generate()
        
        # Save to BytesIO
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        
        # Generate filename
        filename = f"visitors_export_{start_date}_to_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Return Excel file
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response


class DashboardCountsView(APIView):
    """
    Simplified dashboard - only counts (ONE approval per visitor)
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        # 1. Pending approvals - COUNT UNIQUE VISITORS (not sections)
        pending_visitor_ids = VisitorSectionApproval.objects.filter(
            approver=user,
            status='pending'
        ).values_list('visitor_id', flat=True).distinct()
        
        pending_approvals_count = len(pending_visitor_ids)
        
        # 2. Check-in statistics
        visitors = Visitor.objects.filter(
            models.Q(created_by=user) | models.Q(selected_approvers=user)
        ).distinct()
        
        checked_in = visitors.filter(actual_check_in__isnull=False)
        
        early = 0
        on_time = 0
        late = 0
        
        for visitor in checked_in:
            if visitor.designated_check_in and visitor.actual_check_in:
                diff = visitor.actual_check_in - visitor.designated_check_in
                minutes = int(diff.total_seconds() / 60)
                if minutes < 0:
                    early += 1
                elif minutes <= 15:
                    on_time += 1
                else:
                    late += 1
        
        # 3. Scheduled for today
        scheduled_today = visitors.filter(
            designated_check_in__date=today
        ).count()
        
        return Response({
            'success': True,
            'pending_approvals': pending_approvals_count,  # ← ONE per visitor
            'checkin_summary': {
                'total': checked_in.count(),
                'early': early,
                'on_time': on_time,
                'late': late
            },
            'scheduled_today': scheduled_today
        })



# account/views.py - Add this new view class

class VisitorSearchView(APIView):
    """
    Search visitors by name (full_name).
    URL: /account/api/visitors/search/?q=search_term
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request):
        search_query = request.query_params.get('q', '').strip()
        
        if not search_query:
            return Response({
                'success': False,
                'message': 'Please provide a search query',
                'visitors': []
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        # Base query based on user permissions
        if user.is_superuser:
            visitors = Visitor.objects.all()
        else:
            visitors = Visitor.objects.filter(
                models.Q(created_by=user) | 
                models.Q(selected_approvers=user)
            ).distinct()
        
        # Filter by name (case-insensitive partial match)
        visitors = visitors.filter(
            full_name__icontains=search_query
        ).order_by('-created_at')
        
        # Serialize the results
        serializer = VisitorSerializer(visitors, many=True)
        
        # Add approval progress for each visitor
        response_data = serializer.data
        for i, visitor in enumerate(visitors):
            response_data[i]['approval_progress'] = visitor.get_approval_progress()
            response_data[i]['accessible_sections'] = [
                {'id': s.id, 'name': s.name} 
                for s in visitor.get_consensus_approved_sections()
            ]
        
        return Response({
            'success': True,
            'query': search_query,
            'count': visitors.count(),
            'visitors': response_data
        })
    


# account/views.py - Add these views


from django.http import HttpResponse, FileResponse
from django.core.files.base import ContentFile
import base64

# account/views.py - Fixed VisitorQRCodeView

class VisitorQRCodeView(APIView):
    """
    Generate QR code for a visitor
    URL: /account/api/visitors/<int:pk>/qr-code/
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, pk):
        try:
            visitor = Visitor.objects.get(pk=pk)
            site = visitor.site
            
            # Check permission
            if not (request.user.is_superuser or 
                    visitor.created_by == request.user or
                    visitor.selected_approvers.filter(id=request.user.id).exists()):
                return Response(
                    {'error': 'You do not have permission to view this visitor\'s QR code'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get accessible sections for QR data
            accessible_sections = []
            for section in visitor.get_consensus_approved_sections():
                accessible_sections.append({
                    'id': section.id,
                    'name': section.name,
                    'requires_escort': section.requires_escort
                })
            
            # Prepare visitor data as a DICTIONARY (not string)
            visitor_data = {
                'visitor_id': visitor.id,
                'full_name': visitor.full_name,
                'email': visitor.email,
                'phone_number': visitor.phone_number,
                'company_name': visitor.company_name,
                'purpose_of_visit': visitor.purpose_of_visit,
                'designated_check_in': visitor.designated_check_in.isoformat() if visitor.designated_check_in else None,
                'designated_check_out': visitor.designated_check_out.isoformat() if visitor.designated_check_out else None,
                'site': site.name if site else None,
                'status': visitor.status,
                'accessible_sections': accessible_sections
            }
            
            # Generate QR code - pass the DICTIONARY, not a string
            qr_buffer = IDCardGenerator.generate_qr_code(visitor.id, visitor_data)
            
            # Return as image response
            return HttpResponse(
                qr_buffer.getvalue(),
                content_type='image/png',
                headers={
                    'Content-Disposition': f'attachment; filename="visitor_{visitor.id}_qrcode.png"'
                }
            )
            
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error generating QR code: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



class VisitorIDCardView(APIView):
    """
    Generate ID card for a visitor
    URL: /account/api/visitors/<int:pk>/id-card/
    Query param: ?with_photo=true (optional)
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def get(self, request, pk):
        try:
            visitor = Visitor.objects.get(pk=pk)
            
            # Check permission
            if not (request.user.is_superuser or 
                    visitor.created_by == request.user or
                    visitor.selected_approvers.filter(id=request.user.id).exists()):
                return Response(
                    {'error': 'You do not have permission to generate ID card for this visitor'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if visitor can check in
            if visitor.status not in ['approved', 'partially_approved']:
                return Response(
                    {'error': f'Cannot generate ID card. Visitor status is {visitor.status}. Visitor must be approved or partially approved.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get accessible sections
            accessible_sections = []
            for section in visitor.get_consensus_approved_sections():
                accessible_sections.append({
                    'id': section.id,
                    'name': section.name,
                    'requires_escort': section.requires_escort
                })
            
            # Prepare visitor data as DICTIONARY
            visitor_data = {
                'visitor_id': visitor.id,
                'full_name': visitor.full_name,
                'email': visitor.email,
                'phone_number': visitor.phone_number,
                'company_name': visitor.company_name,
                'purpose_of_visit': visitor.purpose_of_visit,
                'designated_check_in': visitor.designated_check_in,
                'designated_check_out': visitor.designated_check_out,
                'site': visitor.site,
                'accessible_sections': accessible_sections
            }
            
            # Generate QR code - pass the DICTIONARY
            qr_buffer = IDCardGenerator.generate_qr_code(visitor.id, visitor_data)
            
            # Check if photo should be included
            with_photo = request.query_params.get('with_photo', 'false').lower() == 'true'
            
            # Generate ID card
            if with_photo and visitor.photo:
                id_card_buffer = IDCardGenerator.generate_id_card(visitor, qr_buffer, with_photo=True)
            else:
                id_card_buffer = IDCardGenerator.generate_simple_id_card(visitor, qr_buffer)
            
            # Return as PDF response
            return FileResponse(
                id_card_buffer,
                as_attachment=True,
                filename=f'visitor_id_card_{visitor.id}_{visitor.full_name.replace(" ", "_")}.pdf',
                content_type='application/pdf'
            )
            
        except Visitor.DoesNotExist:
            return Response({'error': 'Visitor not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error generating ID card: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VisitorBulkIDCardView(APIView):
    """
    Generate ID cards for multiple visitors (bulk)
    URL: /account/api/visitors/bulk-id-cards/
    Body: {"visitor_ids": [1, 2, 3]}
    """
    permission_classes = [IsAuthenticated, IsEmployee]
    
    def post(self, request):
        try:
            from PyPDF2 import PdfMerger
            from io import BytesIO
            
            visitor_ids = request.data.get('visitor_ids', [])
            
            if not visitor_ids:
                return Response(
                    {'error': 'visitor_ids list is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user is superadmin
            if not request.user.is_superuser:
                return Response(
                    {'error': 'Only superadmin can generate bulk ID cards'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            visitors = Visitor.objects.filter(id__in=visitor_ids, status__in=['approved', 'partially_approved'])
            
            if not visitors.exists():
                return Response(
                    {'error': 'No valid visitors found for ID card generation'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Merge all ID cards into one PDF
            merger = PdfMerger()
            
            for visitor in visitors:
                # Prepare visitor data
                visitor_data = {
                    'id': visitor.id,
                    'full_name': visitor.full_name,
                    'email': visitor.email,
                    'phone_number': visitor.phone_number,
                    'company_name': visitor.company_name,
                    'purpose_of_visit': visitor.purpose_of_visit,
                    'designated_check_in': visitor.designated_check_in,
                    'designated_check_out': visitor.designated_check_out,
                    'site': visitor.site,
                    'accessible_sections': []
                }
                
                # Generate QR code
                qr_buffer = IDCardGenerator.generate_qr_code(visitor.id, visitor_data)
                
                # Generate simple ID card (without photo for bulk)
                id_card_buffer = IDCardGenerator.generate_simple_id_card(visitor, qr_buffer)
                
                # Add to merger
                merger.append(id_card_buffer)
            
            # Create merged PDF
            output_buffer = BytesIO()
            merger.write(output_buffer)
            merger.close()
            output_buffer.seek(0)
            
            return FileResponse(
                output_buffer,
                as_attachment=True,
                filename=f'bulk_id_cards_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
                content_type='application/pdf'
            )
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)