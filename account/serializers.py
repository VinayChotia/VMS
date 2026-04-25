from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import CooldownPeriod, Employee, Location, Section, Site, Visitor, VisitorApproval
from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'email', 'full_name', 'department', 'designation', 
                 'is_available', 'profile_picture', 'created_at']
        read_only_fields = ['id', 'created_at']

class EmployeeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'email', 'full_name', 'department', 'designation']

class EmployeeRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = Employee
        fields = ['email', 'full_name', 'department', 'designation', 'password']
    
    def create(self, validated_data):
        user = Employee.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            department=validated_data['department'],
            designation=validated_data['designation']
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        return {'user': user}

class VisitorApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)
    
    class Meta:
        model = VisitorApproval
        fields = ['id', 'approver', 'approver_name', 'status', 'comments', 'responded_at']
        read_only_fields = ['responded_at']


# Add these new serializers after VisitorApprovalSerializer and before VisitorSerializer

class VisitorSectionApprovalSerializer(serializers.ModelSerializer):
    """Serializer for VisitorSectionApproval model"""
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)
    approver_email = serializers.CharField(source='approver.email', read_only=True)
    approver_department = serializers.CharField(source='approver.department', read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True)
    section_code = serializers.CharField(source='section.code', read_only=True)
    
    class Meta:
        from account.models import VisitorSectionApproval
        model = VisitorSectionApproval
        fields = [
            'id', 'section', 'section_name', 'section_code',
            'approver', 'approver_name', 'approver_email', 'approver_department',
            'status', 'comments', 'rejection_reason', 
            'approved_at', 'responded_at'
        ]


class VisitorSectionRequestSerializer(serializers.ModelSerializer):
    """Serializer for VisitorSectionRequest model"""
    requested_by_details = EmployeeSerializer(source='requested_by', read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True)
    section_code = serializers.CharField(source='section.code', read_only=True)
    # Note: VisitorSectionRequest does NOT have a 'status' field
    # It only has requested_at and notes
    
    class Meta:
        from account.models import VisitorSectionRequest
        model = VisitorSectionRequest
        fields = [
            'id', 'section', 'section_name', 'section_code',
            'requested_by', 'requested_by_details', 
            'requested_at', 'notes'  # Removed 'status' field - doesn't exist
        ]


class VisitorSectionTrackingSerializer(serializers.ModelSerializer):
    """Serializer for VisitorSectionTracking model"""
    section_name = serializers.CharField(source='section.name', read_only=True)
    section_code = serializers.CharField(source='section.code', read_only=True)
    checked_in_by_name = serializers.CharField(source='checked_in_by.full_name', read_only=True)
    checked_out_by_name = serializers.CharField(source='checked_out_by.full_name', read_only=True)
    
    class Meta:
        from account.models import VisitorSectionTracking
        model = VisitorSectionTracking
        fields = [
            'id', 'section', 'section_name', 'section_code',
            'section_check_in', 'section_check_out', 
            'duration_minutes', 'status',
            'checked_in_by', 'checked_in_by_name',
            'checked_out_by', 'checked_out_by_name',
            'check_in_notes', 'check_out_notes'
        ]
        read_only_fields = ['duration_minutes']


class SectionApprovalSummarySerializer(serializers.Serializer):
    """Summary of section approvals for a visitor"""
    section_id = serializers.IntegerField()
    section_name = serializers.CharField()
    section_code = serializers.CharField()
    section_type = serializers.CharField()
    requires_escort = serializers.BooleanField()
    location_name = serializers.CharField()
    
    # Approval status
    approval_status = serializers.CharField()  # 'pending', 'approved', 'rejected', 'partially_approved'
    consensus_reached = serializers.BooleanField()
    total_approvers = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    
    # Approver details
    approvers_details = serializers.ListField(child=serializers.DictField())
    
    # Tracking status (if approved)
    tracking_status = serializers.CharField(allow_null=True)
    checked_in = serializers.BooleanField()
    checked_out = serializers.BooleanField()
    check_in_time = serializers.DateTimeField(allow_null=True)
    check_out_time = serializers.DateTimeField(allow_null=True)
    duration_minutes = serializers.IntegerField()
# class VisitorSerializer(serializers.ModelSerializer):
#     created_by_details = EmployeeSerializer(source='created_by', read_only=True)
#     approved_by_details = EmployeeSerializer(source='approved_by', many=True, read_only=True)
#     approval_responses = VisitorApprovalSerializer(many=True, read_only=True)
#     selected_approvers_ids = serializers.PrimaryKeyRelatedField(
#         source='selected_approvers',
#         queryset=Employee.objects.filter(is_available=True),
#         many=True,
#         write_only=True
#     )
    
#     # Read-only computed fields
#     early_arrival_minutes = serializers.IntegerField(read_only=True)
#     late_arrival_minutes = serializers.IntegerField(read_only=True)
#     visit_duration_minutes = serializers.IntegerField(read_only=True)
#     overtime_minutes = serializers.IntegerField(read_only=True)
    
#     class Meta:
#         model = Visitor
#         fields = [
#             'id', 'full_name', 'email', 'phone_number', 'company_name',
#             'purpose_of_visit', 'photo', 'status', 'created_by_details',
#             'selected_approvers_ids', 'approved_by_details', 'approval_responses',
            
#             # Designated times (DateTime)
#             'designated_check_in', 'designated_check_out',
            
#             # Actual times
#             'actual_check_in', 'actual_check_out',
            
#             # Time tracking metrics
#             'early_arrival_minutes', 'late_arrival_minutes',
#             'visit_duration_minutes', 'overtime_minutes',
            
#             # Additional info
#             'vehicle_number', 'id_card_number', 'host_department', 'meeting_room',
#             'check_in_notes', 'check_out_notes',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = [
#             'id', 'status', 'created_at', 'updated_at', 'created_by_details',
#             'actual_check_in', 'actual_check_out',
#             'early_arrival_minutes', 'late_arrival_minutes',
#             'visit_duration_minutes', 'overtime_minutes'
#         ]
    
#     def validate(self, data):
#         # Validate that designated check-in is before designated check-out
#         designated_check_in = data.get('designated_check_in')
#         designated_check_out = data.get('designated_check_out')
        
#         if designated_check_in and designated_check_out:
#             if designated_check_in >= designated_check_out:
#                 raise serializers.ValidationError(
#                     "Designated check-in time must be before designated check-out time"
#                 )
            
#             if designated_check_in < timezone.now():
#                 raise serializers.ValidationError(
#                     "Designated check-in time cannot be in the past"
#                 )
        
#         return data
    
#     # def create(self, validated_data):
#     #     selected_approvers = validated_data.pop('selected_approvers')
#     #     visitor = Visitor.objects.create(**validated_data)
#     #     visitor.selected_approvers.set(selected_approvers)
        
#     #     # Create pending approval records for selected approvers
#     #     for approver in selected_approvers:
#     #         VisitorApproval.objects.create(
#     #             visitor=visitor,
#     #             approver=approver,
#     #             status='pending'
#     #         )
        
#     #     # Trigger notifications for approvers
#     #     from notification.utils import send_approval_request_notification
#     #     for approver in selected_approvers:
#     #         send_approval_request_notification(approver, visitor)
        
#     #     return visitor

#     # def create(self, validated_data):
#     #     """
#     #     Create a visitor with selected approvers and section approvals.
#     #     Handles creation of both VisitorApproval and VisitorSectionApproval records.
#     #     """
#     #     from account.models import VisitorSectionApproval  # Import here to avoid circular imports
        
#     #     # Extract selected approvers from validated data
#     #     selected_approvers = validated_data.pop('selected_approvers')
        
#     #     # Get sections from context (passed from view)
#     #     sections = self.context.get('sections', [])
        
#     #     # Create the visitor
#     #     visitor = Visitor.objects.create(**validated_data)
        
#     #     # Set the selected approvers
#     #     visitor.selected_approvers.set(selected_approvers)
        
#     #     # Create pending approval records for selected approvers (legacy)
#     #     for approver in selected_approvers:
#     #         VisitorApproval.objects.create(
#     #             visitor=visitor,
#     #             approver=approver,
#     #             status='pending'
#     #         )

#     #     for section in sections:
#     #         from .models import VisitorSectionTracking
#     #         VisitorSectionTracking.objects.get_or_create(
#     #                 visitor=visitor,
#     #                 section=section,
#     #                 defaults={'status': 'pending'}
#     #             )
        
#     #     # Create section approval records for EACH approver and EACH section
#     #     for approver in selected_approvers:
#     #         for section in sections:
#     #             VisitorSectionApproval.objects.create(
#     #                 visitor=visitor,
#     #                 section=section,
#     #                 approver=approver,
#     #                 status='pending'
#     #             )
        
#     #     # Send notifications to all approvers
#     #     from notification.utils import send_approval_request_notification
#     #     for approver in selected_approvers:
#     #         send_approval_request_notification(
#     #             approver, 
#     #             visitor,
#     #             sections=sections
#     #         )
        
#     #     return visitor

#     def create(self, validated_data):
#         """
#         Create a visitor with selected approvers and section approvals.
#         Handles creation of VisitorApproval, VisitorSectionRequest, 
#         VisitorSectionApproval, and VisitorSectionTracking records.
#         """
#         from account.models import VisitorSectionApproval, VisitorSectionRequest, VisitorSectionTracking
#         from notification.utils import send_approval_request_notification
        
#         # Extract selected approvers from validated data
#         selected_approvers = validated_data.pop('selected_approvers')
        
#         # Get sections from context (passed from view)
#         sections = self.context.get('sections', [])
        
#         # Create the visitor
#         visitor = Visitor.objects.create(**validated_data)
        
#         # Set the selected approvers
#         visitor.selected_approvers.set(selected_approvers)
        
#         # 1. Create pending approval records for selected approvers (legacy)
#         for approver in selected_approvers:
#             VisitorApproval.objects.create(
#                 visitor=visitor,
#                 approver=approver,
#                 status='pending'
#             )
        
#         # 2. CRITICAL: Create section request records (This is what you're missing!)
#         for section in sections:
#             VisitorSectionRequest.objects.create(
#                 visitor=visitor,
#                 section=section,
#                 requested_by=visitor.created_by
#             )
        
#         # 3. Create section tracking records
#         for section in sections:
#             VisitorSectionTracking.objects.get_or_create(
#                 visitor=visitor,
#                 section=section,
#                 defaults={'status': 'pending'}
#             )
        
#         # 4. Create section approval records for EACH approver and EACH section
#         for approver in selected_approvers:
#             for section in sections:
#                 VisitorSectionApproval.objects.create(
#                     visitor=visitor,
#                     section=section,
#                     approver=approver,
#                     status='pending'
#                 )
        
#         # 5. Send notifications to all approvers
#         for approver in selected_approvers:
#             send_approval_request_notification(
#                 approver, 
#                 visitor,
#                 sections=list(sections)
#             )
        
#         return visitor

class VisitorSectionTrackingSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    section_code = serializers.CharField(source='section.code', read_only=True)
    section_type = serializers.CharField(source='section.section_type', read_only=True)
    requires_escort = serializers.BooleanField(source='section.requires_escort', read_only=True)
    location_name = serializers.CharField(source='section.location.name', read_only=True)
    
    checked_in_by_name = serializers.CharField(source='checked_in_by.full_name', read_only=True)
    checked_out_by_name = serializers.CharField(source='checked_out_by.full_name', read_only=True)
    
    class Meta:
        from account.models import VisitorSectionTracking
        model = VisitorSectionTracking
        fields = [
            'id', 'section', 'section_name', 'section_code', 'section_type',
            'location_name', 'requires_escort',
            'section_check_in', 'section_check_out', 'duration_minutes',
            'status', 'checked_in_by', 'checked_in_by_name',
            'checked_out_by', 'checked_out_by_name',
            'check_in_notes', 'check_out_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['duration_minutes', 'status', 'created_at', 'updated_at']




# class VisitorSerializer(serializers.ModelSerializer):
#     created_by_details = EmployeeSerializer(source='created_by', read_only=True)
#     approved_by_details = EmployeeSerializer(source='approved_by', many=True, read_only=True)
#     visitor_approvals = VisitorApprovalSerializer(many=True, read_only=True)
#     selected_approvers_ids = serializers.PrimaryKeyRelatedField(
#         source='selected_approvers',
#         queryset=Employee.objects.filter(is_available=True),
#         many=True,
#         write_only=True
#     )
    
#     # Read-only computed fields
#     early_arrival_minutes = serializers.IntegerField(read_only=True)
#     late_arrival_minutes = serializers.IntegerField(read_only=True)
#     visit_duration_minutes = serializers.IntegerField(read_only=True)
#     overtime_minutes = serializers.IntegerField(read_only=True)
    
#     # Add section approval related fields
#     visitor_section_approvals = VisitorSectionApprovalSerializer(many=True, read_only=True)
#     section_requests = VisitorSectionRequestSerializer(many=True, read_only=True)
#     section_trackings = VisitorSectionTrackingSerializer(many=True, read_only=True)
#     section_approval_summary = serializers.SerializerMethodField()
#     photo_source = serializers.SerializerMethodField(read_only=True)
#     photo_display_url = serializers.SerializerMethodField(read_only=True)
    
#     class Meta:
#         model = Visitor
#         fields = [
#             'id', 'full_name', 'email', 'phone_number', 'company_name',
#             'purpose_of_visit', 'photo', 'photo_url', 'photo_source', 'photo_display_url', 'status', 'created_by_details',
#             'selected_approvers_ids', 'approved_by_details', 'visitor_approvals',
            
#             # Section approval related fields
#             'visitor_section_approvals', 'section_requests', 'section_trackings',
#             'section_approval_summary',
            
#             # Designated times (DateTime)
#             'designated_check_in', 'designated_check_out',
            
#             # Actual times
#             'actual_check_in', 'actual_check_out',
            
#             # Time tracking metrics
#             'early_arrival_minutes', 'late_arrival_minutes',
#             'visit_duration_minutes', 'overtime_minutes',
            
#             # Additional info
#             'vehicle_number', 'id_card_number', 'host_department', 'meeting_room',
#             'check_in_notes', 'check_out_notes',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = [
#             'id', 'status', 'created_at', 'updated_at', 'created_by_details',
#             'actual_check_in', 'actual_check_out',
#             'early_arrival_minutes', 'late_arrival_minutes',
#             'visit_duration_minutes', 'overtime_minutes',
#             'visitor_section_approvals', 'section_requests', 'section_trackings',
#             'section_approval_summary', 'visitor_approvals','photo_source', 'photo_display_url'
#         ]
    
#     # def get_section_approval_summary(self, obj):
#     #     """
#     #     Generate a summary of section approvals for this visitor.
#     #     Shows the approval status for each section that was requested.
#     #     """
#     #     # Get all section approvals
#     #     section_approvals = obj.visitor_section_approvals.all().select_related('section', 'section__location', 'approver')
        
#     #     if not section_approvals.exists():
#     #         return []
        
#     #     # Group by section
#     #     sections_dict = {}
#     #     for approval in section_approvals:
#     #         section = approval.section
#     #         if section.id not in sections_dict:
#     #             sections_dict[section.id] = {
#     #                 'section_id': section.id,
#     #                 'section_name': section.name,
#     #                 'section_code': section.code,
#     #                 'section_type': section.section_type,
#     #                 'requires_escort': section.requires_escort,
#     #                 'location_name': section.location.name if section.location else None,
#     #                 'approvals': [],
#     #                 'tracking': None
#     #             }
#     #         sections_dict[section.id]['approvals'].append({
#     #             'approver_id': approval.approver.id,
#     #             'approver_name': approval.approver.full_name,
#     #             'approver_email': approval.approver.email,
#     #             'approver_department': approval.approver.department,
#     #             'status': approval.status,
#     #             'comments': approval.comments,
#     #             'rejection_reason': approval.rejection_reason,
#     #             'approved_at': approval.approved_at,
#     #             'responded_at': approval.responded_at
#     #         })
        
#     #     # Get tracking information
#     #     trackings = obj.section_trackings.all().select_related('section')
#     #     for tracking in trackings:
#     #         if tracking.section_id in sections_dict:
#     #             sections_dict[tracking.section_id]['tracking'] = {
#     #                 'status': tracking.status,
#     #                 'section_check_in': tracking.section_check_in,
#     #                 'section_check_out': tracking.section_check_out,
#     #                 'duration_minutes': tracking.duration_minutes
#     #             }
        
#     #     # Calculate summary for each section
#     #     total_approvers = obj.selected_approvers.count()
#     #     summary = []
        
#     #     for section_data in sections_dict.values():
#     #         approvals = section_data['approvals']
#     #         approved_count = sum(1 for a in approvals if a['status'] == 'approved')
#     #         rejected_count = sum(1 for a in approvals if a['status'] == 'rejected')
#     #         pending_count = total_approvers - approved_count - rejected_count
            
#     #         # Determine approval status based on consensus (if 2 approvers)
#     #         if total_approvers == 2:
#     #             if rejected_count > 0:
#     #                 approval_status = 'rejected'
#     #             elif approved_count == 2:
#     #                 approval_status = 'approved'
#     #             else:
#     #                 approval_status = 'pending'
#     #         else:
#     #             if rejected_count > 0:
#     #                 approval_status = 'rejected'
#     #             elif approved_count == total_approvers:
#     #                 approval_status = 'approved'
#     #             elif approved_count > 0:
#     #                 approval_status = 'partially_approved'
#     #             else:
#     #                 approval_status = 'pending'
            
#     #         consensus_reached = (approved_count + rejected_count) == total_approvers
#     #         tracking = section_data.get('tracking')
            
#     #         summary.append({
#     #             'section_id': section_data['section_id'],
#     #             'section_name': section_data['section_name'],
#     #             'section_code': section_data['section_code'],
#     #             'section_type': section_data['section_type'],
#     #             'requires_escort': section_data['requires_escort'],
#     #             'location_name': section_data['location_name'],
#     #             'approval_status': approval_status,
#     #             'consensus_reached': consensus_reached,
#     #             'total_approvers': total_approvers,
#     #             'approved_count': approved_count,
#     #             'rejected_count': rejected_count,
#     #             'pending_count': pending_count,
#     #             'approvers_details': approvals,
#     #             'tracking_status': tracking['status'] if tracking else 'not_started',
#     #             'checked_in': tracking['section_check_in'] is not None if tracking else False,
#     #             'checked_out': tracking['section_check_out'] is not None if tracking else False,
#     #             'check_in_time': tracking['section_check_in'] if tracking else None,
#     #             'check_out_time': tracking['section_check_out'] if tracking else None,
#     #             'duration_minutes': tracking['duration_minutes'] if tracking else 0,
#     #         })
        
#     #     return summary
    
#     def get_section_approval_summary(self, obj):
#         """
#         Generate a summary of section approvals for this visitor.
#         Shows the approval status for each section that was requested.
#         """
#         from account.models import VisitorSectionRequest, VisitorSectionApproval, VisitorSectionTracking
        
#         # Get all section approvals for this visitor
#         section_approvals = obj.visitor_section_approvals.all().select_related('section', 'section__location', 'approver')
        
#         if not section_approvals.exists():
#             return []
        
#         # Group by section
#         sections_dict = {}
#         total_approvers = obj.selected_approvers.count()
        
#         for approval in section_approvals:
#             section = approval.section
#             if section.id not in sections_dict:
#                 sections_dict[section.id] = {
#                     'section_id': section.id,
#                     'section_name': section.name,
#                     'section_code': section.code,
#                     'section_type': section.section_type,
#                     'requires_escort': section.requires_escort,
#                     'location_name': section.location.name if section.location else None,
#                     'approvals': [],
#                     'tracking': None
#                 }
#             sections_dict[section.id]['approvals'].append({
#                 'approver_id': approval.approver.id,
#                 'approver_name': approval.approver.full_name,
#                 'approver_email': approval.approver.email,
#                 'approver_department': approval.approver.department,
#                 'status': approval.status,
#                 'comments': approval.comments,
#                 'rejection_reason': approval.rejection_reason,
#                 'approved_at': approval.approved_at,
#                 'responded_at': approval.responded_at
#             })
        
#         # Get tracking information
#         trackings = obj.section_trackings.all().select_related('section')
#         for tracking in trackings:
#             if tracking.section_id in sections_dict:
#                 sections_dict[tracking.section_id]['tracking'] = {
#                     'status': tracking.status,
#                     'section_check_in': tracking.section_check_in,
#                     'section_check_out': tracking.section_check_out,
#                     'duration_minutes': tracking.duration_minutes
#                 }
        
#         # Calculate summary for each section
#         summary = []
        
#         for section_data in sections_dict.values():
#             approvals = section_data['approvals']
#             approved_count = sum(1 for a in approvals if a['status'] == 'approved')
#             rejected_count = sum(1 for a in approvals if a['status'] == 'rejected')
#             pending_count = total_approvers - approved_count - rejected_count
            
#             # CRITICAL FIX: Determine approval status
#             # For 2 approvers, section is approved ONLY if BOTH approved
#             if total_approvers == 2:
#                 if rejected_count > 0:
#                     approval_status = 'rejected'
#                 elif approved_count == 2:  # BOTH approvers approved
#                     approval_status = 'approved'
#                 elif approved_count == 1:
#                     approval_status = 'partially_approved'  # One approved, one pending
#                 else:
#                     approval_status = 'pending'
#             else:
#                 # For other number of approvers
#                 if rejected_count > 0:
#                     approval_status = 'rejected'
#                 elif approved_count == total_approvers:
#                     approval_status = 'approved'
#                 elif approved_count > 0:
#                     approval_status = 'partially_approved'
#                 else:
#                     approval_status = 'pending'
            
#             consensus_reached = (approved_count + rejected_count) == total_approvers
#             tracking = section_data.get('tracking')
            
#             summary.append({
#                 'section_id': section_data['section_id'],
#                 'section_name': section_data['section_name'],
#                 'section_code': section_data['section_code'],
#                 'section_type': section_data['section_type'],
#                 'requires_escort': section_data['requires_escort'],
#                 'location_name': section_data['location_name'],
#                 'approval_status': approval_status,
#                 'consensus_reached': consensus_reached,
#                 'total_approvers': total_approvers,
#                 'approved_count': approved_count,
#                 'rejected_count': rejected_count,
#                 'pending_count': pending_count,
#                 'approvers_details': approvals,
#                 'tracking_status': tracking['status'] if tracking else 'not_started',
#                 'checked_in': tracking['section_check_in'] is not None if tracking else False,
#                 'checked_out': tracking['section_check_out'] is not None if tracking else False,
#                 'check_in_time': tracking['section_check_in'] if tracking else None,
#                 'check_out_time': tracking['section_check_out'] if tracking else None,
#                 'duration_minutes': tracking['duration_minutes'] if tracking else 0,
#             })
        
#         return summary
    
#     def get_photo_source(self, obj):
#         """Indicate where the photo came from"""
#         if obj.photo:
#             return 'upload'
#         elif obj.photo_url:
#             return 'url'
#         return None
    
#     def get_photo_display_url(self, obj):
#         """Get the URL to display the photo (from either source)"""
#         if obj.photo and hasattr(obj.photo, 'url'):
#             request = self.context.get('request')
#             if request:
#                 return request.build_absolute_uri(obj.photo.url)
#             return obj.photo.url
#         elif obj.photo_url:
#             return obj.photo_url
#         return None
    
#     def validate_photo(self, value):
#         """Validate uploaded image"""
#         if value:
#             # Check file size (max 5MB)
#             if value.size > 5 * 1024 * 1024:
#                 raise serializers.ValidationError("Image size cannot exceed 5MB")
            
#             # Check file extension
#             allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
#             ext = value.name.split('.')[-1].lower()
#             if ext not in allowed_extensions:
#                 raise serializers.ValidationError(
#                     f"Only {', '.join(allowed_extensions)} formats are allowed"
#                 )
#         return value
    
#     def validate_photo_url(self, value):
#         """Validate the photo URL"""
#         if value:
#             # Validate URL format
#             url_validator = URLValidator()
#             try:
#                 url_validator(value)
#             except ValidationError:
#                 raise serializers.ValidationError("Invalid URL format")
            
#             # Optional: Check if URL points to an image
#             import requests
#             from django.core.files.base import ContentFile
#             import imghdr
            
#             # You can optionally validate that the URL returns an image
#             # This is optional and adds network overhead
#             try:
#                 response = requests.head(value, timeout=5)
#                 content_type = response.headers.get('content-type', '')
#                 if not content_type.startswith('image/'):
#                     # This is a warning, not an error - you might want to keep it flexible
#                     pass
#             except:
#                 # If URL is unreachable, still allow it but maybe add a warning
#                 pass
        
#         return value
    

#     def validate(self, data):
#         # Validate that designated check-in is before designated check-out
#         designated_check_in = data.get('designated_check_in')
#         designated_check_out = data.get('designated_check_out')
#         photo = data.get('photo')
#         photo_url = data.get('photo_url')
        
#         if not photo and not photo_url:
#             # Photo is optional, so this is not required
#             pass
        
#         # Don't allow both to be provided simultaneously (optional)
#         if photo and photo_url:
#             raise serializers.ValidationError(
#                 "Please provide either an image file or an image URL, not both"
#             )
        
#         if designated_check_in and designated_check_out:
#             if designated_check_in >= designated_check_out:
#                 raise serializers.ValidationError(
#                     "Designated check-in time must be before designated check-out time"
#                 )
            
#             if designated_check_in < timezone.now():
#                 raise serializers.ValidationError(
#                     "Designated check-in time cannot be in the past"
#                 )
        
#         return data
    
#     def create(self, validated_data):
#         """
#         Create a visitor with selected approvers and section approvals.
#         Handles creation of VisitorApproval, VisitorSectionRequest, 
#         VisitorSectionApproval, and VisitorSectionTracking records.
#         """
#         from account.models import VisitorSectionApproval, VisitorSectionRequest, VisitorSectionTracking
#         from notification.utils import send_approval_request_notification
        
#         # Extract selected approvers from validated data
#         selected_approvers = validated_data.pop('selected_approvers')
        
#         # Get sections from context (passed from view)
#         sections = self.context.get('sections', [])
        
#         # Create the visitor
#         visitor = Visitor.objects.create(**validated_data)
#         if validated_data.get('photo_url') and not validated_data.get('photo'):
#             # Optional: Download and save the image locally
#             self.download_and_save_photo(visitor, validated_data['photo_url'])
        
#         # Set the selected approvers
#         visitor.selected_approvers.set(selected_approvers)
        
#         # 1. Create pending approval records for selected approvers (legacy)
#         for approver in selected_approvers:
#             VisitorApproval.objects.create(
#                 visitor=visitor,
#                 approver=approver,
#                 status='pending'
#             )
        
#         # 2. Create section request records
#         for section in sections:
#             VisitorSectionRequest.objects.create(
#                 visitor=visitor,
#                 section=section,
#                 requested_by=visitor.created_by
#             )
        
#         # 3. Create section tracking records
#         for section in sections:
#             VisitorSectionTracking.objects.get_or_create(
#                 visitor=visitor,
#                 section=section,
#                 defaults={'status': 'pending'}
#             )
        
#         # 4. Create section approval records for EACH approver and EACH section
#         for approver in selected_approvers:
#             for section in sections:
#                 VisitorSectionApproval.objects.create(
#                     visitor=visitor,
#                     section=section,
#                     approver=approver,
#                     status='pending'
#                 )
        
#         # 5. Send notifications to all approvers
#         for approver in selected_approvers:
#             send_approval_request_notification(
#                 approver, 
#                 visitor,
#                 sections=list(sections)
#             )
        
#         return visitor


# account/serializers.py

from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Visitor, Employee, VisitorApproval, VisitorSectionApproval, VisitorSectionRequest, VisitorSectionTracking
from .serializers import EmployeeSerializer, VisitorApprovalSerializer, VisitorSectionApprovalSerializer, VisitorSectionRequestSerializer, VisitorSectionTrackingSerializer


class VisitorSerializer(serializers.ModelSerializer):
    created_by_details = EmployeeSerializer(source='created_by', read_only=True)
    approved_by_details = EmployeeSerializer(source='approved_by', many=True, read_only=True)
    visitor_approvals = VisitorApprovalSerializer(many=True, read_only=True)
    
    # CHANGE: Use ListField instead of PrimaryKeyRelatedField
    selected_approvers_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True
    )
    
    # Read-only computed fields
    early_arrival_minutes = serializers.IntegerField(read_only=True)
    late_arrival_minutes = serializers.IntegerField(read_only=True)
    visit_duration_minutes = serializers.IntegerField(read_only=True)
    overtime_minutes = serializers.IntegerField(read_only=True)
    
    # Add section approval related fields
    visitor_section_approvals = VisitorSectionApprovalSerializer(many=True, read_only=True)
    section_requests = VisitorSectionRequestSerializer(many=True, read_only=True)
    section_trackings = VisitorSectionTrackingSerializer(many=True, read_only=True)
    section_approval_summary = serializers.SerializerMethodField()
    
    # ADD: Photo display field
    photo_display_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Visitor
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'company_name',
            'purpose_of_visit', 'photo', 'photo_url', 'photo_display_url', 'status', 
            'created_by_details', 'selected_approvers_ids', 'approved_by_details', 
            'visitor_approvals', 'visitor_section_approvals', 'section_requests', 
            'section_trackings', 'section_approval_summary', 'designated_check_in', 
            'designated_check_out', 'actual_check_in', 'actual_check_out',
            'early_arrival_minutes', 'late_arrival_minutes', 'visit_duration_minutes', 
            'overtime_minutes', 'vehicle_number', 'id_card_number', 'host_department', 
            'meeting_room', 'check_in_notes', 'check_out_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'created_at', 'updated_at', 'created_by_details',
            'actual_check_in', 'actual_check_out', 'early_arrival_minutes', 
            'late_arrival_minutes', 'visit_duration_minutes', 'overtime_minutes',
            'visitor_section_approvals', 'section_requests', 'section_trackings',
            'section_approval_summary', 'visitor_approvals', 'photo_display_url'
        ]
    
    def get_photo_display_url(self, obj):
        """Get the URL to display the photo (from either source)"""
        if obj.photo and hasattr(obj.photo, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        elif obj.photo_url:
            return obj.photo_url
        return None
    
    def get_section_approval_summary(self, obj):
        """
        Generate a summary of section approvals for this visitor.
        Shows the approval status for each section that was requested.
        """
        from account.models import VisitorSectionRequest, VisitorSectionApproval, VisitorSectionTracking
        
        # Get all section approvals for this visitor
        section_approvals = obj.visitor_section_approvals.all().select_related('section', 'section__location', 'approver')
        
        if not section_approvals.exists():
            return []
        
        # Group by section
        sections_dict = {}
        total_approvers = obj.selected_approvers.count()
        
        for approval in section_approvals:
            section = approval.section
            if section.id not in sections_dict:
                sections_dict[section.id] = {
                    'section_id': section.id,
                    'section_name': section.name,
                    'section_code': section.code,
                    'section_type': section.section_type,
                    'requires_escort': section.requires_escort,
                    'location_name': section.location.name if section.location else None,
                    'approvals': [],
                    'tracking': None
                }
            sections_dict[section.id]['approvals'].append({
                'approver_id': approval.approver.id,
                'approver_name': approval.approver.full_name,
                'approver_email': approval.approver.email,
                'approver_department': approval.approver.department,
                'status': approval.status,
                'comments': approval.comments,
                'rejection_reason': approval.rejection_reason,
                'approved_at': approval.approved_at,
                'responded_at': approval.responded_at
            })
        
        # Get tracking information
        trackings = obj.section_trackings.all().select_related('section')
        for tracking in trackings:
            if tracking.section_id in sections_dict:
                sections_dict[tracking.section_id]['tracking'] = {
                    'status': tracking.status,
                    'section_check_in': tracking.section_check_in,
                    'section_check_out': tracking.section_check_out,
                    'duration_minutes': tracking.duration_minutes
                }
        
        # Calculate summary for each section
        summary = []
        
        for section_data in sections_dict.values():
            approvals = section_data['approvals']
            approved_count = sum(1 for a in approvals if a['status'] == 'approved')
            rejected_count = sum(1 for a in approvals if a['status'] == 'rejected')
            pending_count = total_approvers - approved_count - rejected_count
            
            # Determine approval status
            if total_approvers == 2:
                if rejected_count > 0:
                    approval_status = 'rejected'
                elif approved_count == 2:
                    approval_status = 'approved'
                elif approved_count == 1:
                    approval_status = 'partially_approved'
                else:
                    approval_status = 'pending'
            else:
                if rejected_count > 0:
                    approval_status = 'rejected'
                elif approved_count == total_approvers:
                    approval_status = 'approved'
                elif approved_count > 0:
                    approval_status = 'partially_approved'
                else:
                    approval_status = 'pending'
            
            consensus_reached = (approved_count + rejected_count) == total_approvers
            tracking = section_data.get('tracking')
            
            summary.append({
                'section_id': section_data['section_id'],
                'section_name': section_data['section_name'],
                'section_code': section_data['section_code'],
                'section_type': section_data['section_type'],
                'requires_escort': section_data['requires_escort'],
                'location_name': section_data['location_name'],
                'approval_status': approval_status,
                'consensus_reached': consensus_reached,
                'total_approvers': total_approvers,
                'approved_count': approved_count,
                'rejected_count': rejected_count,
                'pending_count': pending_count,
                'approvers_details': approvals,
                'tracking_status': tracking['status'] if tracking else 'not_started',
                'checked_in': tracking['section_check_in'] is not None if tracking else False,
                'checked_out': tracking['section_check_out'] is not None if tracking else False,
                'check_in_time': tracking['section_check_in'] if tracking else None,
                'check_out_time': tracking['section_check_out'] if tracking else None,
                'duration_minutes': tracking['duration_minutes'] if tracking else 0,
            })
        
        return summary
    
    def validate_photo(self, value):
        """Validate uploaded image"""
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Image size cannot exceed 5MB")
            
            # Check file extension
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            ext = value.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f"Only {', '.join(allowed_extensions)} formats are allowed"
                )
        return value
    
    def validate_photo_url(self, value):
        """Validate the photo URL"""
        if value:
            url_validator = URLValidator()
            try:
                url_validator(value)
            except ValidationError:
                raise serializers.ValidationError("Invalid URL format")
        return value
    
    def validate_selected_approvers_ids(self, value):
        """Validate that exactly 2 approvers are selected and they exist"""
        if not value or len(value) != 2:
            raise serializers.ValidationError("Exactly 2 approvers must be selected")
        
        # Check if approvers exist
        approvers = Employee.objects.filter(id__in=value, is_available=True)
        if approvers.count() != 2:
            raise serializers.ValidationError("Both approvers must be valid and available employees")
        
        # Check if they are different
        if value[0] == value[1]:
            raise serializers.ValidationError("The two approvers must be different employees")
        
        return value

    def validate(self, data):
        """Validate that either photo or photo_url is provided, but not both"""
        photo = data.get('photo')
        photo_url = data.get('photo_url')
        
        # Allow both to be empty (photo optional)
        # If both are provided, raise error
        if photo and photo_url:
            raise serializers.ValidationError(
                "Please provide either an image file or an image URL, not both"
            )
        
        # Validate designated times
        designated_check_in = data.get('designated_check_in')
        designated_check_out = data.get('designated_check_out')
        
        if designated_check_in and designated_check_out:
            if designated_check_in >= designated_check_out:
                raise serializers.ValidationError(
                    "Designated check-in time must be before designated check-out time"
                )
            
            if designated_check_in < timezone.now():
                raise serializers.ValidationError(
                    "Designated check-in time cannot be in the past"
                )
        
        return data
    
    def create(self, validated_data):
        """
        Create a visitor with selected approvers and section approvals.
        Handles both photo upload and photo URL.
        """
        from account.models import VisitorSectionApproval, VisitorSectionRequest, VisitorSectionTracking
        from notification.utils import send_approval_request_notification
        
        # Extract selected approvers from validated data
        selected_approver_ids = validated_data.pop('selected_approvers_ids')
        selected_approvers = Employee.objects.filter(id__in=selected_approver_ids)
        
        # Get sections from context (passed from view)
        sections = self.context.get('sections', [])
        
        # Create the visitor
        visitor = Visitor.objects.create(**validated_data)
        
        # Set the selected approvers
        visitor.selected_approvers.set(selected_approvers)
        
        # 1. Create pending approval records for selected approvers (legacy)
        for approver in selected_approvers:
            VisitorApproval.objects.create(
                visitor=visitor,
                approver=approver,
                status='pending'
            )
        
        # 2. Create section request records
        for section in sections:
            VisitorSectionRequest.objects.create(
                visitor=visitor,
                section=section,
                requested_by=visitor.created_by
            )
        
        # 3. Create section tracking records
        for section in sections:
            VisitorSectionTracking.objects.get_or_create(
                visitor=visitor,
                section=section,
                defaults={'status': 'pending'}
            )
        
        # 4. Create section approval records for EACH approver and EACH section
        for approver in selected_approvers:
            for section in sections:
                VisitorSectionApproval.objects.create(
                    visitor=visitor,
                    section=section,
                    approver=approver,
                    status='pending'
                )
        
        # 5. Send notifications to all approvers
        for approver in selected_approvers:
            send_approval_request_notification(
                approver, 
                visitor,
                sections=list(sections)
            )
        
        return visitor


class VisitorApprovalResponseSerializer(serializers.Serializer):
    visitor_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['approved', 'rejected'])
    comments = serializers.CharField(required=False, allow_blank=True)

class VisitorCheckInSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)

class VisitorCheckOutSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)

class VisitorTimeUpdateSerializer(serializers.Serializer):
    """Serializer for updating check-in/out times manually"""
    actual_check_in = serializers.DateTimeField(required=False)
    actual_check_out = serializers.DateTimeField(required=False)
    check_in_notes = serializers.CharField(required=False, allow_blank=True)
    check_out_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        actual_check_in = data.get('actual_check_in')
        actual_check_out = data.get('actual_check_out')
        
        if actual_check_in and actual_check_out:
            if actual_check_in >= actual_check_out:
                raise serializers.ValidationError(
                    "Check-in time must be before check-out time"
                )
        
        if actual_check_in and actual_check_in > timezone.now():
            raise serializers.ValidationError(
                "Check-in time cannot be in the future"
            )
        
        return data

class VisitorDateRangeSerializer(serializers.Serializer):
    """Serializer for filtering visitors by date range"""
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    status = serializers.ChoiceField(
        choices=['all', 'checked_in', 'checked_out', 'no_show', 'pending', 'approved', 'rejected'],
        required=False,
        default='all'
    )
    
    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date must be before end date")
        return data
    
class SectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Section
        fields = '__all__'
        

class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = '__all__'

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class CooldownPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = CooldownPeriod
        fields = '__all__'
        


class SectionCheckInSerializer(serializers.Serializer):
    section_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)


class SectionCheckOutSerializer(serializers.Serializer):
    section_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)


class VisitorWithSectionsSerializer(VisitorSerializer):
    """Extended visitor serializer with section tracking data"""
    section_trackings = VisitorSectionTrackingSerializer(many=True, read_only=True)
    approved_sections_detail = serializers.SerializerMethodField()
    
    class Meta(VisitorSerializer.Meta):
        fields = VisitorSerializer.Meta.fields + ['section_trackings', 'approved_sections_detail']
    
    def get_approved_sections_detail(self, obj):
        """Get detailed approved sections with tracking status"""
        approved_sections = obj.get_consensus_approved_sections()
        section_trackings = {st.section_id: st for st in obj.section_trackings.all()}
        
        result = []
        for section in approved_sections:
            tracking = section_trackings.get(section.id)
            result.append({
                'id': section.id,
                'name': section.name,
                'code': section.code,
                'section_type': section.section_type,
                'requires_escort': section.requires_escort,
                'location': section.location.name if section.location else None,
                'tracking_status': tracking.status if tracking else 'pending',
                'check_in_time': tracking.section_check_in if tracking else None,
                'check_out_time': tracking.section_check_out if tracking else None,
                'duration_minutes': tracking.duration_minutes if tracking else 0,
            })
        
        return result


class VisitorExportSerializer(serializers.ModelSerializer):
    """Serializer for exporting visitor data to Excel"""
    
    # Basic Info
    visitor_name = serializers.CharField(source='full_name')
    visitor_email = serializers.CharField(source='email')
    visitor_phone = serializers.CharField(source='phone_number')
    
    # Company & Purpose
    company = serializers.CharField(source='company_name')
    purpose = serializers.CharField(source='purpose_of_visit')
    
    # Site & Status
    site_name = serializers.CharField(source='site.name', default='')
    visitor_status = serializers.CharField(source='status')
    
    # Times
    designated_check_in = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    designated_check_out = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    actual_check_in = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', allow_null=True)
    actual_check_out = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', allow_null=True)
    
    # Time Metrics
    early_arrival_minutes = serializers.IntegerField()
    late_arrival_minutes = serializers.IntegerField()
    visit_duration_minutes = serializers.IntegerField()
    overtime_minutes = serializers.IntegerField()
    
    # Staff Info
    created_by_name = serializers.CharField(source='created_by.full_name')
    approver_names = serializers.SerializerMethodField()
    
    # Section Tracking
    sections_accessed = serializers.SerializerMethodField()
    total_sections_visited = serializers.SerializerMethodField()
    total_time_in_sections = serializers.SerializerMethodField()
    
    # Additional Info
    vehicle_number = serializers.CharField()
    id_card_number = serializers.CharField()
    host_department = serializers.CharField()
    meeting_room = serializers.CharField()
    
    # Timestamps
    created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    updated_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    
    class Meta:
        model = Visitor
        fields = [
            'id', 'visitor_name', 'visitor_email', 'visitor_phone',
            'company', 'purpose', 'site_name', 'visitor_status',
            'designated_check_in', 'designated_check_out',
            'actual_check_in', 'actual_check_out',
            'early_arrival_minutes', 'late_arrival_minutes',
            'visit_duration_minutes', 'overtime_minutes',
            'created_by_name', 'approver_names',
            'sections_accessed', 'total_sections_visited', 'total_time_in_sections',
            'vehicle_number', 'id_card_number', 'host_department', 'meeting_room',
            'created_at', 'updated_at'
        ]
    
    def get_approver_names(self, obj):
        """Get comma-separated list of approver names"""
        return ', '.join([approver.full_name for approver in obj.selected_approvers.all()])
    
    def get_sections_accessed(self, obj):
        """Get detailed section access information"""
        sections = []
        for tracking in obj.section_trackings.all():
            sections.append({
                'section_name': tracking.section.name,
                'check_in': tracking.section_check_in.strftime('%Y-%m-%d %H:%M:%S') if tracking.section_check_in else '',
                'check_out': tracking.section_check_out.strftime('%Y-%m-%d %H:%M:%S') if tracking.section_check_out else '',
                'duration_minutes': tracking.duration_minutes,
                'status': tracking.status
            })
        return sections
    
    def get_total_sections_visited(self, obj):
        """Get count of sections visited (completed)"""
        return obj.section_trackings.filter(status='completed').count()
    
    def get_total_time_in_sections(self, obj):
        """Get total time spent in all sections"""
        return sum([t.duration_minutes for t in obj.section_trackings.all()])