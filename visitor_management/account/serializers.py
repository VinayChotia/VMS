from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import CooldownPeriod, Employee, Location, Section, Site, Visitor, VisitorApproval

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

class VisitorSerializer(serializers.ModelSerializer):
    created_by_details = EmployeeSerializer(source='created_by', read_only=True)
    approved_by_details = EmployeeSerializer(source='approved_by', many=True, read_only=True)
    approval_responses = VisitorApprovalSerializer(many=True, read_only=True)
    selected_approvers_ids = serializers.PrimaryKeyRelatedField(
        source='selected_approvers',
        queryset=Employee.objects.filter(is_available=True),
        many=True,
        write_only=True
    )
    
    # Read-only computed fields
    early_arrival_minutes = serializers.IntegerField(read_only=True)
    late_arrival_minutes = serializers.IntegerField(read_only=True)
    visit_duration_minutes = serializers.IntegerField(read_only=True)
    overtime_minutes = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Visitor
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'company_name',
            'purpose_of_visit', 'photo', 'status', 'created_by_details',
            'selected_approvers_ids', 'approved_by_details', 'approval_responses',
            
            # Designated times (DateTime)
            'designated_check_in', 'designated_check_out',
            
            # Actual times
            'actual_check_in', 'actual_check_out',
            
            # Time tracking metrics
            'early_arrival_minutes', 'late_arrival_minutes',
            'visit_duration_minutes', 'overtime_minutes',
            
            # Additional info
            'vehicle_number', 'id_card_number', 'host_department', 'meeting_room',
            'check_in_notes', 'check_out_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'created_at', 'updated_at', 'created_by_details',
            'actual_check_in', 'actual_check_out',
            'early_arrival_minutes', 'late_arrival_minutes',
            'visit_duration_minutes', 'overtime_minutes'
        ]
    
    def validate(self, data):
        # Validate that designated check-in is before designated check-out
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
        selected_approvers = validated_data.pop('selected_approvers')
        visitor = Visitor.objects.create(**validated_data)
        visitor.selected_approvers.set(selected_approvers)
        
        # Create pending approval records for selected approvers
        for approver in selected_approvers:
            VisitorApproval.objects.create(
                visitor=visitor,
                approver=approver,
                status='pending'
            )
        
        # Trigger notifications for approvers
        from notification.utils import send_approval_request_notification
        for approver in selected_approvers:
            send_approval_request_notification(approver, visitor)
        
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
        