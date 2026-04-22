from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone


class Site(models.Model):
    """Top-level premises - managed by Superadmin only"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    daily_capacity_limit = models.PositiveIntegerField(default=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Location(models.Model):
    """Building or area within a Site - managed by Superadmin only"""
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    floor_number = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['site', 'code']
        ordering = ['site__name', 'name']
    
    def __str__(self):
        return f"{self.site.name} - {self.name}"


class Section(models.Model):
    """Specific room or restricted area within a Location - managed by Superadmin only"""
    SECTION_TYPES = [
        ('general', 'General Area'),
        ('restricted', 'Restricted Area'),
        ('lab', 'Laboratory'),
        ('server', 'Server Room'),
        ('executive', 'Executive Floor'),
        ('conference', 'Conference Room'),
        ('other', 'Other'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES, default='general')
    daily_capacity = models.PositiveIntegerField(default=50)
    requires_escort = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['location', 'code']
        ordering = ['location__site__name', 'location__name', 'name']
    
    def __str__(self):
        return f"{self.location.site.name} / {self.location.name} / {self.name}"


# ========== NEW: COOLDOWN MODEL (Simple - Site Level Only) ==========



class EmployeeManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Employee(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    is_available = models.BooleanField(default=True)
    profile_picture = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    objects = EmployeeManager()
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    class Meta:
        ordering = ['full_name']


class Visitor(models.Model):
    VISITOR_STATUS = [
        ('pending', 'Pending Approval'),
        ('partially_approved', 'Partially Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic Information
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    company_name = models.CharField(max_length=255, blank=True)
    purpose_of_visit = models.TextField()
    photo = models.URLField(blank=True, null=True)

    # site related connection
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitors')
    approved_sections = models.ManyToManyField(Section, through='VisitorSectionApproval', related_name='approved_visitors')
    
    # Approval tracking
    status = models.CharField(max_length=20, choices=VISITOR_STATUS, default='pending')
    created_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='created_visitors')
    selected_approvers = models.ManyToManyField(Employee, related_name='assigned_approvals')
    approved_by = models.ManyToManyField(Employee, through='VisitorApproval', related_name='approved_visitors')
    
    # Designated Visit Times (Scheduled) - Using DateTime fields directly
    designated_check_in = models.DateTimeField(null=True, blank=True, db_index=True)
    designated_check_out = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Actual Visit Times (Real)
    actual_check_in = models.DateTimeField(null=True, blank=True, db_index=True)
    actual_check_out = models.DateTimeField(null=True, blank=True, db_index=True)
    early_arrival_minutes = models.IntegerField(default=0, help_text="Minutes early for check-in")
    late_arrival_minutes = models.IntegerField(default=0, help_text="Minutes late for check-in")
    visit_duration_minutes = models.IntegerField(default=0, help_text="Actual visit duration in minutes")
    overtime_minutes = models.IntegerField(default=0, help_text="Minutes stayed beyond designated check-out")
    vehicle_number = models.CharField(max_length=50, blank=True)
    id_card_number = models.CharField(max_length=100, blank=True)
    host_department = models.CharField(max_length=100, blank=True)
    meeting_room = models.CharField(max_length=100, blank=True)
    check_in_notes = models.TextField(blank=True, help_text="Notes taken during check-in")
    check_out_notes = models.TextField(blank=True, help_text="Notes taken during check-out")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    requested_sections = models.ManyToManyField(Section, through='VisitorSectionRequest', related_name='requested_visitors')
    
    def __str__(self):
        return f"{self.full_name} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Validate that designated check-in is before designated check-out
        if self.designated_check_in and self.designated_check_out:
            if self.designated_check_in >= self.designated_check_out:
                raise ValueError("Designated check-in time must be before designated check-out time")
        
        # Calculate time metrics if actual check-in exists
        if self.actual_check_in and self.designated_check_in:
            time_diff = self.actual_check_in - self.designated_check_in
            minutes_diff = int(time_diff.total_seconds() / 60)
            
            if minutes_diff < 0:
                self.early_arrival_minutes = abs(minutes_diff)
                self.late_arrival_minutes = 0
            else:
                self.early_arrival_minutes = 0
                self.late_arrival_minutes = minutes_diff
        
        # Calculate visit duration if both actual times exist
        if self.actual_check_in and self.actual_check_out:
            if self.actual_check_out <= self.actual_check_in:
                raise ValueError("Check-out time must be after check-in time")
            
            duration = self.actual_check_out - self.actual_check_in
            self.visit_duration_minutes = int(duration.total_seconds() / 60)
        
        # Calculate overtime if actual check-out exceeds designated check-out
        if self.actual_check_out and self.designated_check_out:
            if self.actual_check_out > self.designated_check_out:
                overtime = self.actual_check_out - self.designated_check_out
                self.overtime_minutes = int(overtime.total_seconds() / 60)
            else:
                self.overtime_minutes = 0
        
        super().save(*args, **kwargs)
    
    def check_in(self, notes=None):
        """Record actual check-in time"""
        if self.status != 'approved':
            raise ValueError("Visitor must be approved before check-in")
        
        if self.actual_check_in:
            raise ValueError(f"Visitor already checked in at {self.actual_check_in}")
        
        self.actual_check_in = timezone.now()
        self.status = 'checked_in'
        
        if notes:
            self.check_in_notes = notes
        
        self.save()
        
        # Determine if visitor is early or late
        if self.early_arrival_minutes > 0:
            timing_message = f" (Early by {self.early_arrival_minutes} minutes)"
        elif self.late_arrival_minutes > 0:
            timing_message = f" (Late by {self.late_arrival_minutes} minutes)"
        else:
            timing_message = " (On time)"
        
        return {
            'check_in_time': self.actual_check_in,
            'timing_message': timing_message,
            'early_arrival_minutes': self.early_arrival_minutes,
            'late_arrival_minutes': self.late_arrival_minutes
        }
    
    def check_out(self, notes=None):
        """Record actual check-out time"""
        if not self.actual_check_in:
            raise ValueError("Visitor must check in first")
        
        if self.actual_check_out:
            raise ValueError(f"Visitor already checked out at {self.actual_check_out}")
        
        self.actual_check_out = timezone.now()
        self.status = 'checked_out'
        
        if notes:
            self.check_out_notes = notes
        
        self.save()
        
        response = {
            'check_out_time': self.actual_check_out,
            'visit_duration_minutes': self.visit_duration_minutes
        }
        
        if self.overtime_minutes > 0:
            response['message'] = f"Checked out with {self.overtime_minutes} minutes overtime"
            response['overtime_minutes'] = self.overtime_minutes
        
        return response
    
    def mark_no_show(self):
        """Mark visitor as no-show if they didn't check in on scheduled day"""
        if self.status == 'approved' and self.designated_check_in:
            # Check if the scheduled date has passed
            if timezone.now() > self.designated_check_in:
                self.status = 'no_show'
                self.save()
                return True
        return False
    
    def is_late(self, threshold_minutes=15):
        """Check if visitor is late by more than threshold minutes"""
        if self.actual_check_in and self.designated_check_in:
            late_by = (self.actual_check_in - self.designated_check_in).total_seconds() / 60
            return late_by > threshold_minutes
        return False
    
    def is_overtime(self):
        """Check if visitor stayed beyond designated time"""
        if self.actual_check_out and self.designated_check_out:
            return self.actual_check_out > self.designated_check_out
        return False
    
    def get_visit_summary(self):
        """Get a summary of the visit"""
        summary = {
            'visitor_name': self.full_name,
            'status': self.status,
            'designated_check_in': self.designated_check_in,
            'designated_check_out': self.designated_check_out,
            'actual_check_in': self.actual_check_in,
            'actual_check_out': self.actual_check_out,
        }
        
        if self.actual_check_in:
            summary['arrival_status'] = 'early' if self.early_arrival_minutes > 0 else 'late' if self.late_arrival_minutes > 0 else 'on_time'
            summary['arrival_minutes_offset'] = self.early_arrival_minutes or self.late_arrival_minutes
        
        if self.actual_check_out:
            summary['duration_minutes'] = self.visit_duration_minutes
            summary['overtime_minutes'] = self.overtime_minutes
        
        return summary
    
    def check_approval_status(self):
        """Update visitor status based on approvals"""
        total_approvers = self.selected_approvers.count()
        approved_count = self.visitor_approvals.filter(status='approved').count()
        rejected_count = self.visitor_approvals.filter(status='rejected').count()
        
        if rejected_count > 0:
            new_status = 'rejected'
        elif approved_count >= 2:  # Both approvers approved
            new_status = 'approved'
        elif approved_count > 0:
            new_status = 'partially_approved'
        else:
            new_status = 'pending'
        
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])
        
        return self.status
    
    def get_approved_sections_list(self):
        """Get list of sections that have been approved for this visitor"""
        return self.visitor_section_approvals.filter(status='approved').select_related('section')
    
    def get_pending_sections_list(self):
        """Get list of sections still pending approval"""
        return self.visitor_section_approvals.filter(status='pending').select_related('section')
    
    def get_rejected_sections_list(self):
        """Get list of sections that were rejected"""
        return self.visitor_section_approvals.filter(status='rejected').select_related('section')
    
    def check_overall_approval_status(self):
        """Update visitor status based on section approvals"""
        total_sections = self.visitor_section_approvals.count()
        approved_count = self.visitor_section_approvals.filter(status='approved').count()
        rejected_count = self.visitor_section_approvals.filter(status='rejected').count()
        
        if rejected_count == total_sections:
            new_status = 'rejected'
        elif approved_count == total_sections:
            new_status = 'approved'
        elif approved_count > 0:
            new_status = 'partially_approved'
        else:
            new_status = 'pending'
        
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])
        
        return self.status
    
    def has_section_access(self, section):
        """Check if visitor has approval for a specific section"""
        return self.visitor_section_approvals.filter(section=section, status='approved').exists()
    
    def get_access_matrix(self):
        """Get complete access matrix for security personnel"""
        matrix = []
        for section_approval in self.visitor_section_approvals.select_related('section', 'section__location', 'section__location__site'):
            matrix.append({
                'site': section_approval.section.location.site.name,
                'location': section_approval.section.location.name,
                'section': section_approval.section.name,
                'status': section_approval.status,
                'requires_escort': section_approval.section.requires_escort,
                'approved_by': section_approval.approved_by.full_name if section_approval.approved_by else None,
                'approved_at': section_approval.approved_at,
                'rejection_reason': section_approval.rejection_reason,
            })
        return matrix
    
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['designated_check_in']),
            models.Index(fields=['designated_check_out']),
            models.Index(fields=['actual_check_in']),
            models.Index(fields=['actual_check_out']),
            models.Index(fields=['status']),
            models.Index(fields=['designated_check_in', 'status']),  # Composite index for common queries
            models.Index(fields = ['site'])
        ]


class VisitorSectionRequest(models.Model):
    """Sections requested by the creator for this visitor"""
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='section_requests')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='visitor_requests')
    requested_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='requested_sections')
    requested_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Why this section is needed")
    
    class Meta:
        unique_together = ['visitor', 'section']
        ordering = ['section__location__site__name', 'section__location__name', 'section__name']
    
    def __str__(self):
        return f"{self.visitor.full_name} -> {self.section.name}"


# ========== NEW: Visitor Section Approval Model ==========
# This tracks which sections each APPROVER approved/rejected

class VisitorSectionApproval(models.Model):
    """Section-wise approval record - each approver can approve/reject specific sections"""
    APPROVAL_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='visitor_section_approvals')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='visitor_approvals')
    approver = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='section_approvals')
    status = models.CharField(max_length=10, choices=APPROVAL_STATUS, default='pending')
    comments = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True, help_text="Required if status is rejected")
    approved_by = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True, related_name='approved_sections')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['visitor', 'section', 'approver']
        ordering = ['section__location__site__name', 'section__location__name', 'section__name']
    
    def save(self, *args, **kwargs):
        if self.status == 'approved' and not self.approved_at:
            self.approved_at = timezone.now()
            self.approved_by = self.approver
        if self.status == 'rejected' and not self.rejection_reason:
            raise ValueError("Rejection reason is required when rejecting a section")
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.visitor.full_name} - {self.section.name} - {self.status} by {self.approver.full_name}"



class VisitorApproval(models.Model):
    APPROVAL_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='visitor_approvals')
    approver = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='approval_responses')
    status = models.CharField(max_length=10, choices=APPROVAL_STATUS, default='pending')
    comments = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)


    def save(self,*args,**kwargs):
        if self.status != 'pending' and not self.responded_at:
            self.responded_at = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        unique_together = ['visitor', 'approver']
        ordering = ['-responded_at']

class CooldownPeriod(models.Model):
    """Cooldown period for a site - Superadmin only"""
    COOLDOWN_TYPES = [
        ('daily', 'Daily Recurring'),
        ('one_time', 'One Time'),
        ('emergency', 'Emergency'),
    ]
    
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='cooldowns')
    cooldown_type = models.CharField(max_length=20, choices=COOLDOWN_TYPES, default='one_time')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    start_time = models.TimeField(null=True, blank=True, help_text="For daily cooldowns")
    end_time = models.TimeField(null=True, blank=True, help_text="For daily cooldowns")
    reason = models.TextField()
    created_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='created_cooldowns')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_datetime']
    
    def is_active_now(self):
        if not self.is_active:
            return False
        now = timezone.now()
        if self.cooldown_type == 'daily' and self.start_time and self.end_time:
            current_time = now.time()
            if self.start_time <= self.end_time:
                return self.start_time <= current_time <= self.end_time
            else:
                return current_time >= self.start_time or current_time <= self.end_time
        else:
            return self.start_datetime <= now <= self.end_datetime
