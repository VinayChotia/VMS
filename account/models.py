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
    
    def get_today_visitor_count(self):
        """Get today's visitor count for this site"""
        today = timezone.now().date()
        return self.visitors.filter(
            actual_check_in__date=today,
            status__in=['checked_in', 'checked_out']
        ).count()
    
    def is_capacity_available(self):
        """Check if site has capacity for more visitors today"""
        return self.get_today_visitor_count() < self.daily_capacity_limit
    
    def is_on_cooldown(self):
        """Check if site is currently in cooldown"""
        for cooldown in self.cooldowns.filter(is_active=True):
            if cooldown.is_active_now():
                return True
        return False
    
    def get_active_cooldown(self):
        """Get active cooldown if any"""
        for cooldown in self.cooldowns.filter(is_active=True):
            if cooldown.is_active_now():
                return cooldown
        return None


class Location(models.Model):
    """Building or area within a Site - managed by Superadmin only"""
    site = models.ForeignKey('account.Site', on_delete=models.CASCADE, related_name='locations')
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
    
    location = models.ForeignKey('account.Location', on_delete=models.CASCADE, related_name='sections')
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
    
    def get_today_visitor_count(self):
        """Get today's visitor count for this section"""
        today = timezone.now().date()
        return self.visitor_approvals.filter(
            status='approved',
            visitor__actual_check_in__date=today,
            visitor__status__in=['checked_in', 'checked_out']
        ).values('visitor').distinct().count()
    
    def is_capacity_available(self):
        """Check if section has capacity for more visitors today"""
        return self.get_today_visitor_count() < self.daily_capacity


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




class CooldownPeriod(models.Model):
    """Cooldown period for a site - Superadmin only"""
    COOLDOWN_TYPES = [
        ('daily', 'Daily Recurring'),
        ('one_time', 'One Time'),
        ('emergency', 'Emergency'),
    ]
    
    site = models.ForeignKey('account.Site', on_delete=models.CASCADE, related_name='cooldowns')
    cooldown_type = models.CharField(max_length=20, choices=COOLDOWN_TYPES, default='one_time')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    start_time = models.TimeField(null=True, blank=True, help_text="For daily cooldowns")
    end_time = models.TimeField(null=True, blank=True, help_text="For daily cooldowns")
    reason = models.TextField()
    created_by = models.ForeignKey('account.Employee', on_delete=models.CASCADE, related_name='created_cooldowns')
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



class VisitorSectionRequest(models.Model):
    """Sections requested by the creator for this visitor"""
    visitor = models.ForeignKey('account.Visitor', on_delete=models.CASCADE, related_name='section_requests')
    section = models.ForeignKey('account.Section', on_delete=models.CASCADE, related_name='visitor_requests')
    requested_by = models.ForeignKey('account.Employee', on_delete=models.CASCADE, related_name='requested_sections')
    requested_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Why this section is needed")
    
    class Meta:
        unique_together = ['visitor', 'section']
        ordering = ['section__name']  # Simplified ordering
    
    def __str__(self):
        return f"{self.visitor.full_name} -> {self.section.name}"


class VisitorSectionApproval(models.Model):
    """Section-wise approval record - each approver can approve/reject specific sections"""
    APPROVAL_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    visitor = models.ForeignKey('account.Visitor', on_delete=models.CASCADE, related_name='visitor_section_approvals')
    section = models.ForeignKey('account.Section', on_delete=models.CASCADE, related_name='visitor_approvals')
    approver = models.ForeignKey('account.Employee', on_delete=models.CASCADE, related_name='section_approvals')
    status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default='pending')
    comments = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True, help_text="Required if status is rejected")
    approved_by = models.ForeignKey('account.Employee', on_delete=models.CASCADE, null=True, blank=True, related_name='approved_sections')
    approved_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)  # ADD THIS FIELD
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['visitor', 'section', 'approver']
        ordering = ['section__name']  # Simplified ordering
    
    # def save(self, *args, **kwargs):
    #     if self.status == 'approved' and not self.approved_at:
    #         self.approved_at = timezone.now()
    #         self.approved_by = self.approver
    #     if self.status != 'pending' and not self.responded_at:
    #         self.responded_at = timezone.now()
    #     if self.status == 'rejected' and not self.rejection_reason:
    #         raise ValueError("Rejection reason is required when rejecting a section")
    #     super().save(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #     # Your existing save logic (before saving)
    #     if self.status == 'approved' and not self.approved_at:
    #         self.approved_at = timezone.now()
    #         self.approved_by = self.approver
    #     if self.status != 'pending' and not self.responded_at:
    #         self.responded_at = timezone.now()
    #     if self.status == 'rejected' and not self.rejection_reason:
    #         raise ValueError("Rejection reason is required when rejecting a section")
        
    #     # Save the section approval first
    #     super().save(*args, **kwargs)
        
    #     # AFTER saving, update the visitor status
    #     # This ensures we have the latest data
    #     if hasattr(self, 'visitor') and self.visitor:
    #         # Update individual approver's overall status
    #         self.visitor.update_approver_status(self.approver)
    #         # Update the overall visitor status
    #         self.visitor.update_overall_visitor_status()

    def save(self, *args, **kwargs):
        # Debug: Check field lengths before save
        for field in self._meta.fields:
            if hasattr(field, 'max_length') and field.max_length:
                value = getattr(self, field.name, None)
                if value and isinstance(value, str) and len(value) > field.max_length:
                    print(f"❌ ERROR: Field '{field.name}' value too long before save!")
                    print(f"   Value: '{value}'")
                    print(f"   Length: {len(value)}")
                    print(f"   Max: {field.max_length}")
                    # Truncate to prevent error
                    setattr(self, field.name, value[:field.max_length])
                    print(f"   Truncated to: '{value[:field.max_length]}'")
        
        # Your existing save logic
        if self.status == 'approved' and not self.approved_at:
            self.approved_at = timezone.now()
            self.approved_by = self.approver
        if self.status != 'pending' and not self.responded_at:
            self.responded_at = timezone.now()
        if self.status == 'rejected' and not self.rejection_reason:
            raise ValueError("Rejection reason is required when rejecting a section")
        
        # Save the section approval first
        super().save(*args, **kwargs)
        
        # AFTER saving, update the visitor status
        if hasattr(self, 'visitor') and self.visitor:
            try:
                # Update individual approver's overall status
                print(f"🔍 Calling update_approver_status for {self.approver}")
                self.visitor.update_approver_status(self.approver)
                
                # Update the overall visitor status
                print(f"🔍 Calling update_overall_visitor_status")
                self.visitor.update_overall_visitor_status()
            except Exception as e:
                print(f"⚠️ Error in status update: {e}")
                import traceback
                traceback.print_exc()
                # Don't re-raise - we already saved the section approval
    
    def __str__(self):
        return f"{self.visitor.full_name} - {self.section.name} - {self.status} by {self.approver.full_name}"


class VisitorApproval(models.Model):
    APPROVAL_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('partially_approved', 'Partially Approved'),  # Add this option
    ]
    
    visitor = models.ForeignKey('account.Visitor', on_delete=models.CASCADE, related_name='visitor_approvals')
    approver = models.ForeignKey('account.Employee', on_delete=models.CASCADE, related_name='approval_responses')
    status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default='pending')
    comments = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    # def save(self, *args, **kwargs):
    #     if self.status != 'pending' and not self.responded_at:
    #         self.responded_at = timezone.now()
    #     super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.status != 'pending' and not self.responded_at:
            self.responded_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Update visitor status
        if hasattr(self, 'visitor') and self.visitor:
            self.visitor.update_overall_visitor_status()
    
    class Meta:
        unique_together = ['visitor', 'approver']
        ordering = ['-responded_at']



# models.py - Complete Updated Visitor Model

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
    # photo = models.URLField(blank=True, null=True)
    photo = models.ImageField(upload_to='visitor_photos/', blank=True, null=True, max_length=500)
    photo_url = models.URLField(blank=True, null=True, max_length=500)

    # site related connection
    site = models.ForeignKey('account.Site', on_delete=models.SET_NULL, null=True, blank=True, related_name='visitors')
    approved_sections = models.ManyToManyField(
        'account.Section', through='account.VisitorSectionApproval', related_name='approved_visitors')
    
    # Approval tracking
    status = models.CharField(max_length=20, choices=VISITOR_STATUS, default='pending')
    created_by = models.ForeignKey('account.Employee', on_delete=models.CASCADE, related_name='created_visitors')
    selected_approvers = models.ManyToManyField('account.Employee', related_name='assigned_approvals')
    approved_by = models.ManyToManyField('account.Employee', through='account.VisitorApproval', related_name='approved_visitors')
    
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
    requested_sections = models.ManyToManyField('account.Section', through='account.VisitorSectionRequest', related_name='requested_visitors')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['designated_check_in']),
            models.Index(fields=['designated_check_out']),
            models.Index(fields=['actual_check_in']),
            models.Index(fields=['actual_check_out']),
            models.Index(fields=['status']),
            models.Index(fields=['designated_check_in', 'status']),
            models.Index(fields=['site'])
        ]
    
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
    
    # def check_in(self, notes=None):
    #     """Record actual check-in time"""
    #     if self.status != 'approved':
    #         raise ValueError("Visitor must be approved before check-in")
        
    #     if self.actual_check_in:
    #         raise ValueError(f"Visitor already checked in at {self.actual_check_in}")
        
    #     self.actual_check_in = timezone.now()
    #     self.status = 'checked_in'
        
    #     if notes:
    #         self.check_in_notes = notes
        
    #     self.save()
        
    #     # Determine if visitor is early or late
    #     if self.early_arrival_minutes > 0:
    #         timing_message = f" (Early by {self.early_arrival_minutes} minutes)"
    #     elif self.late_arrival_minutes > 0:
    #         timing_message = f" (Late by {self.late_arrival_minutes} minutes)"
    #     else:
    #         timing_message = " (On time)"
        
    #     return {
    #         'check_in_time': self.actual_check_in,
    #         'timing_message': timing_message,
    #         'early_arrival_minutes': self.early_arrival_minutes,
    #         'late_arrival_minutes': self.late_arrival_minutes
    #     }
    
    def check_in(self, notes=None):
        """Record actual check-in time"""
        # FIX: Allow both 'approved' and 'partially_approved' status
        if self.status not in ['approved', 'partially_approved']:
            raise ValueError("Visitor must be approved or partially approved before check-in")
        
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
    
    # def check_approval_status(self):
    #     """Update visitor status based on approvals"""
    #     total_approvers = self.selected_approvers.count()
    #     approved_count = self.visitor_approvals.filter(status='approved').count()
    #     rejected_count = self.visitor_approvals.filter(status='rejected').count()
        
    #     if rejected_count > 0:
    #         new_status = 'rejected'
    #     elif approved_count >= 2:  # Both approvers approved
    #         new_status = 'approved'
    #     elif approved_count > 0:
    #         new_status = 'partially_approved'
    #     else:
    #         new_status = 'pending'
        
    #     if self.status != new_status:
    #         self.status = new_status
    #         self.save(update_fields=['status'])
        
    #     return self.status
    
    # In your models.py, update the Visitor model's check_approval_status method:

    # def check_approval_status(self):
    #     """
    #     Update visitor status based on section approvals.
    #     Status becomes 'partially_approved' if at least one section is approved 
    #     by consensus (both approvers) and others are pending.
    #     """
    #     total_approvers = self.selected_approvers.count()
        
    #     # Get all section approvals
    #     all_section_approvals = self.visitor_section_approvals.all()
        
    #     if not all_section_approvals.exists():
    #         # Fall back to legacy approval logic if no sections
    #         total_approvers = self.selected_approvers.count()
    #         approved_count = self.visitor_approvals.filter(status='approved').count()
    #         rejected_count = self.visitor_approvals.filter(status='rejected').count()
            
    #         if rejected_count > 0:
    #             new_status = 'rejected'
    #         elif approved_count >= 2:
    #             new_status = 'approved'
    #         elif approved_count > 0:
    #             new_status = 'partially_approved'
    #         else:
    #             new_status = 'pending'
    #     else:
    #         # Get unique sections
    #         section_ids = all_section_approvals.values_list('section_id', flat=True).distinct()
            
    #         # Track section statuses
    #         sections_approved = 0
    #         sections_partially_approved = 0
    #         sections_pending = 0
    #         sections_rejected = 0
            
    #         for section_id in section_ids:
    #             section_approvals = all_section_approvals.filter(section_id=section_id)
    #             approved_count = section_approvals.filter(status='approved').count()
    #             rejected_count = section_approvals.filter(status='rejected').count()
                
    #             if total_approvers == 2:
    #                 # For 2 approvers, need BOTH to approve for section to be approved
    #                 if rejected_count > 0:
    #                     sections_rejected += 1
    #                 elif approved_count == 2:
    #                     sections_approved += 1
    #                 elif approved_count == 1:
    #                     sections_partially_approved += 1
    #                 else:
    #                     sections_pending += 1
    #             else:
    #                 # For other numbers of approvers
    #                 if rejected_count > 0:
    #                     sections_rejected += 1
    #                 elif approved_count == total_approvers:
    #                     sections_approved += 1
    #                 elif approved_count > 0:
    #                     sections_partially_approved += 1
    #                 else:
    #                     sections_pending += 1
            
    #         # Determine overall status
    #         if sections_rejected > 0:
    #             new_status = 'rejected'
    #         elif sections_approved > 0 and (sections_pending > 0 or sections_partially_approved > 0):
    #             new_status = 'partially_approved'  # At least one section approved, some pending
    #         elif sections_approved > 0 and sections_pending == 0 and sections_partially_approved == 0:
    #             new_status = 'approved'  # All sections approved
    #         elif sections_partially_approved > 0:
    #             new_status = 'partially_approved'  # Some sections have partial approval
    #         else:
    #             new_status = 'pending'
        
    #     if self.status != new_status:
    #         self.status = new_status
    #         self.save(update_fields=['status'])
        
    #     return self.status

    def get_approved_sections_list(self):
        """Get list of sections that have been approved for this visitor"""
        return self.visitor_section_approvals.filter(status='approved').select_related('section')
    
    def get_pending_sections_list(self):
        """Get list of sections still pending approval"""
        return self.visitor_section_approvals.filter(status='pending').select_related('section')
    
    def get_rejected_sections_list(self):
        """Get list of sections that were rejected"""
        return self.visitor_section_approvals.filter(status='rejected').select_related('section')
    
    # ========== NEW CONSENSUS-BASED APPROVAL METHODS ==========
    
    def check_overall_approval_status(self):
        """
        Update visitor status based on CONSENSUS approval.
        A section is APPROVED only if BOTH approvers approved it.
        Overall status is APPROVED if at least ONE section has consensus.
        """
        total_approvers = self.selected_approvers.count()
        
        # If not exactly 2 approvers, use old logic
        if total_approvers != 2:
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
        
        # NEW CONSENSUS LOGIC FOR EXACTLY 2 APPROVERS
        all_approvals = self.visitor_section_approvals.all()
        
        if not all_approvals.exists():
            if self.status != 'pending':
                self.status = 'pending'
                self.save(update_fields=['status'])
            return 'pending'
        
        # Check if ANY section is rejected by ANY approver
        if all_approvals.filter(status='rejected').exists():
            new_status = 'rejected'
        else:
            # Count sections that have BOTH approvers approved
            sections_with_consensus = 0
            for section in self.requested_sections.all():
                section_approvals = self.visitor_section_approvals.filter(section=section)
                approved_count = section_approvals.filter(status='approved').count()
                
                if approved_count == 2:  # Both approvers approved
                    sections_with_consensus += 1
            
            if sections_with_consensus > 0:
                new_status = 'approved'
            else:
                # Check if any approvals exist
                any_approvals = all_approvals.filter(status='approved').exists()
                if any_approvals:
                    new_status = 'partially_approved'
                else:
                    new_status = 'pending'
        
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])
        
        return self.status
    
    def get_consensus_approved_sections(self):
        """
        Get sections that have been approved by BOTH approvers.
        These are the ONLY sections the visitor can access.
        """
        total_approvers = self.selected_approvers.count()
        
        # FIX: Use VisitorSectionApproval to get sections
        if total_approvers != 2:
            # Return sections that have at least one approval
            approved_section_ids = self.visitor_section_approvals.filter(
                status='approved'
            ).values_list('section_id', flat=True).distinct()
            return Section.objects.filter(id__in=approved_section_ids)
        
        # Consensus logic for exactly 2 approvers
        # Get all sections that have 2 approved records
        from django.db.models import Count, Q
        
        section_ids = self.visitor_section_approvals.values('section_id').annotate(
            approved_count=Count('id', filter=Q(status='approved'))
        ).filter(approved_count=2).values_list('section_id', flat=True)
        
        return Section.objects.filter(id__in=section_ids)

        
    def get_access_matrix(self):
        """
        Get complete access matrix showing which sections are accessible.
        A section is accessible ONLY if BOTH approvers approved it.
        """
        total_approvers = self.selected_approvers.count()
        matrix = []
        
        for section_approval in self.visitor_section_approvals.select_related(
            'section', 'section__location', 'section__location__site', 'approver'
        ):
            # Get all approvals for this section to check consensus
            section = section_approval.section
            all_approvals_for_section = self.visitor_section_approvals.filter(section=section)
            approved_count = all_approvals_for_section.filter(status='approved').count()
            rejected_count = all_approvals_for_section.filter(status='rejected').count()
            
            # Determine if section is accessible (only if exactly 2 approvers both approved)
            is_accessible = False
            if total_approvers == 2:
                is_accessible = (approved_count == 2 and rejected_count == 0)
            else:
                is_accessible = (section_approval.status == 'approved')
            
            matrix.append({
                'site': section_approval.section.location.site.name,
                'location': section_approval.section.location.name,
                'section_id': section.id,
                'section_name': section_approval.section.name,
                'status': section_approval.status,
                'requires_escort': section_approval.section.requires_escort,
                'approved_by': section_approval.approved_by.full_name if section_approval.approved_by else None,
                'approved_at': section_approval.approved_at,
                'rejection_reason': section_approval.rejection_reason,
                'is_accessible': is_accessible,
                'consensus_info': {
                    'total_approvers': total_approvers,
                    'approved_by_count': approved_count,
                    'rejected_by_count': rejected_count,
                    'needs_both_approvers': total_approvers == 2,
                    'access_granted': is_accessible
                }
            })
        
        return matrix
    
    # def get_approval_progress(self):
    #     """
    #     Get detailed approval progress for consensus-based approval.
    #     Shows progress per section and overall status.
    #     """
    #     total_approvers = self.selected_approvers.count()
        
    #     # FIX: Use VisitorSectionApproval to get unique sections instead of requested_sections
    #     # Get unique section IDs from VisitorSectionApproval records
    #     section_ids = self.visitor_section_approvals.values_list('section_id', flat=True).distinct()
    #     sections = Section.objects.filter(id__in=section_ids)
        
    #     sections_data = []
    #     sections_with_consensus = 0
    #     sections_partially_approved = 0
    #     sections_pending = 0
        
    #     for section in sections:
    #         section_approvals = self.visitor_section_approvals.filter(section=section)
    #         approved_count = section_approvals.filter(status='approved').count()
    #         rejected_count = section_approvals.filter(status='rejected').count()
    #         pending_count = total_approvers - approved_count - rejected_count
            
    #         has_consensus = False
    #         if total_approvers == 2:
    #             has_consensus = (approved_count == 2 and rejected_count == 0)
    #             if has_consensus:
    #                 sections_with_consensus += 1
    #             elif approved_count == 1:
    #                 sections_partially_approved += 1
    #             elif approved_count == 0 and rejected_count == 0:
    #                 sections_pending += 1
    #         else:
    #             # Old logic for non-2 approvers
    #             if approved_count == total_approvers:
    #                 sections_with_consensus += 1
    #             elif approved_count > 0:
    #                 sections_partially_approved += 1
    #             else:
    #                 sections_pending += 1
            
    #         sections_data.append({
    #             'section_id': section.id,
    #             'section_name': section.name,
    #             'total_approvers': total_approvers,
    #             'approved_count': approved_count,
    #             'rejected_count': rejected_count,
    #             'pending_count': pending_count,
    #             'has_consensus': has_consensus,
    #             'is_accessible': has_consensus,
    #             'progress_percentage': round((approved_count / total_approvers) * 100, 2) if total_approvers > 0 else 0
    #         })
        
    #     total_sections = len(sections)
        
    #     return {
    #         'approval_mode': 'consensus_based' if total_approvers == 2 else 'standard',
    #         'total_sections': total_sections,
    #         'total_approvers': total_approvers,
    #         'sections_accessible': sections_with_consensus,
    #         'sections_partially_approved': sections_partially_approved,
    #         'sections_pending': sections_pending,
    #         'overall_progress_percentage': round((sections_with_consensus / total_sections) * 100, 2) if total_sections > 0 else 0,
    #         'consensus_rule': 'Section accessible only if BOTH approvers approve it' if total_approvers == 2 else 'Standard approval rules apply',
    #         'sections': sections_data
    #     }


    def get_approval_progress(self):
        """
        Get detailed approval progress for consensus-based approval.
        Shows progress per section and overall status.
        """
        total_approvers = self.selected_approvers.count()
        
        # Get unique section IDs from VisitorSectionApproval records
        section_ids = self.visitor_section_approvals.values_list('section_id', flat=True).distinct()
        sections = Section.objects.filter(id__in=section_ids)
        
        sections_data = []
        sections_with_consensus = 0
        sections_partially_approved = 0
        sections_pending = 0
        
        for section in sections:
            section_approvals = self.visitor_section_approvals.filter(section=section)
            approved_count = section_approvals.filter(status='approved').count()
            rejected_count = section_approvals.filter(status='rejected').count()
            pending_count = total_approvers - approved_count - rejected_count
            
            has_consensus = False
            if total_approvers == 2:
                has_consensus = (approved_count == 2 and rejected_count == 0)
                if has_consensus:
                    sections_with_consensus += 1
                elif approved_count == 1:
                    sections_partially_approved += 1
                elif approved_count == 0 and rejected_count == 0:
                    sections_pending += 1
            else:
                # Old logic for non-2 approvers
                if approved_count == total_approvers:
                    sections_with_consensus += 1
                elif approved_count > 0:
                    sections_partially_approved += 1
                else:
                    sections_pending += 1
            
            sections_data.append({
                'section_id': section.id,
                'section_name': section.name,
                'total_approvers': total_approvers,
                'approved_count': approved_count,
                'rejected_count': rejected_count,
                'pending_count': pending_count,
                'has_consensus': has_consensus,
                'is_accessible': has_consensus,
                'progress_percentage': round((approved_count / total_approvers) * 100, 2) if total_approvers > 0 else 0
            })
        
        total_sections = len(sections)
        
        return {
            'approval_mode': 'consensus_based' if total_approvers == 2 else 'standard',
            'total_sections': total_sections,
            'total_approvers': total_approvers,
            'sections_accessible': sections_with_consensus,
            'accessible_sections_count': sections_with_consensus,  # ← ADD THIS LINE
            'sections_partially_approved': sections_partially_approved,
            'sections_pending': sections_pending,
            'overall_progress_percentage': round((sections_with_consensus / total_sections) * 100, 2) if total_sections > 0 else 0,
            'consensus_rule': 'Section accessible only if BOTH approvers approve it' if total_approvers == 2 else 'Standard approval rules apply',
            'sections': sections_data
        }

    # def can_check_in(self):
    #     """
    #     Check if visitor can check in.
    #     Visitor can check in ONLY if at least ONE section has consensus approval (both approvers approved it).
    #     """
    #     if self.status != 'approved':
    #         return False, f"Visitor status is {self.status}, not approved"
        
    #     consensus_approved = self.get_consensus_approved_sections()
        
    #     if len(consensus_approved) == 0:
    #         total_approvers = self.selected_approvers.count()
    #         if total_approvers == 2:
    #             return False, "No sections have been approved by BOTH approvers. Visitor cannot check in. Both approvers must approve each section for access to be granted."
    #         else:
    #             return False, "No approved sections found. Visitor cannot check in."
        
    #     return True, f"Ready for check-in. Access granted to {len(consensus_approved)} section(s)."
    
    def can_check_in(self):
        """
        Check if visitor can check in.
        Visitor can check in if at least ONE section has consensus approval.
        """
        # FIX: Allow partially_approved status as well
        if self.status not in ['approved', 'partially_approved']:
            return False, f"Visitor status is {self.status}, cannot check in. Status must be 'approved' or 'partially_approved'."
        
        consensus_approved = self.get_consensus_approved_sections()
        
        if len(consensus_approved) == 0:
            total_approvers = self.selected_approvers.count()
            if total_approvers == 2:
                return False, "No sections have been approved by BOTH approvers. Visitor cannot check in. Both approvers must approve at least one section for access to be granted."
            else:
                return False, "No approved sections found. Visitor cannot check in."
        
        return True, f"Ready for check-in. Access granted to {len(consensus_approved)} section(s)."
    
    def has_section_access(self, section):
        """
        Check if visitor has access to a specific section.
        For 2 approvers: Returns True only if BOTH approved this section.
        """
        total_approvers = self.selected_approvers.count()
        
        if total_approvers == 2:
            section_approvals = self.visitor_section_approvals.filter(section=section)
            approved_count = section_approvals.filter(status='approved').count()
            return approved_count == 2
        else:
            return self.visitor_section_approvals.filter(section=section, status='approved').exists()
        
    
    def can_check_out_site(self):
        """
        Check if visitor can check out of the site.
        Returns: (can_checkout, message)
        """
        # Check if visitor has any active section check-ins
        active_sections = self.section_trackings.filter(
            section_check_in__isnull=False,
            section_check_out__isnull=True
        )
        
        if active_sections.exists():
            section_names = [s.section.name for s in active_sections]
            return False, f"Visitor must check out of these sections first: {', '.join(section_names)}"
        
        return True, "Ready to check out of site"


    def get_active_sections(self):
        """Get sections where visitor is currently checked in"""
        return self.section_trackings.filter(
            section_check_in__isnull=False,
            section_check_out__isnull=True
        ).select_related('section')
    
    # def update_approver_status(self, approver):
    #     """
    #     Update the overall VisitorApproval status for a specific approver
    #     based on their section approvals.
    #     """
    #     # Get all sections for this visitor
    #     all_sections = self.visitor_section_approvals.filter(approver=approver)
    #     total_sections = all_sections.count()
        
    #     if total_sections == 0:
    #         return
        
    #     approved_sections = all_sections.filter(status='approved').count()
    #     rejected_sections = all_sections.filter(status='rejected').count()
        
    #     # Get or create the overall visitor approval record
    #     visitor_approval, created = VisitorApproval.objects.get_or_create(
    #         visitor=self,
    #         approver=approver,
    #         defaults={'status': 'pending'}
    #     )
        
    #     # Update status based on section approvals
    #     if rejected_sections > 0:
    #         new_status = 'rejected'
    #     elif approved_sections == total_sections:
    #         new_status = 'approved'
    #     elif approved_sections > 0:
    #         new_status = 'partially_approved'  # New status for partial approval
    #     else:
    #         new_status = 'pending'
        
    #     if visitor_approval.status != new_status:
    #         visitor_approval.status = new_status
    #         if new_status != 'pending':
    #             visitor_approval.responded_at = timezone.now()
    #         visitor_approval.save()
    #         print(f"Updated approver {approver.email} status to {new_status}")
        
    #     return visitor_approval

    def update_approver_status(self, approver):
        """
        Update the overall VisitorApproval status for a specific approver
        based on their section approvals.
        """
        # Get all sections for this visitor
        all_sections = self.visitor_section_approvals.filter(approver=approver)
        total_sections = all_sections.count()
        
        if total_sections == 0:
            return
        
        approved_sections = all_sections.filter(status='approved').count()
        rejected_sections = all_sections.filter(status='rejected').count()
        
        # Get or create the overall visitor approval record
        visitor_approval, created = VisitorApproval.objects.get_or_create(
            visitor=self,
            approver=approver,
            defaults={'status': 'pending'}
        )
        
        # Update status based on section approvals
        if rejected_sections > 0:
            # If any section is rejected, the approver's status is rejected
            new_status = 'rejected'
        elif approved_sections > 0:
            # If at least one section is approved, status is partially_approved
            # (even if not all sections are approved yet)
            new_status = 'partially_approved'
        else:
            new_status = 'pending'
        
        if visitor_approval.status != new_status:
            visitor_approval.status = new_status
            if new_status != 'pending':
                visitor_approval.responded_at = timezone.now()
            visitor_approval.save()
            print(f"Updated approver {approver.email} status to {new_status}")
        
        return visitor_approval
    # def update_overall_visitor_status(self):
    #     """
    #     Update the overall visitor status based on section approvals.
    #     Status becomes 'partially_approved' if at least one section is approved
    #     and others are pending.
    #     """
    #     all_section_approvals = self.visitor_section_approvals.all()
        
    #     if not all_section_approvals.exists():
    #         # No sections - use legacy approval logic
    #         total_approvers = self.selected_approvers.count()
    #         approved_count = self.visitor_approvals.filter(status='approved').count()
    #         rejected_count = self.visitor_approvals.filter(status='rejected').count()
            
    #         if rejected_count > 0:
    #             new_status = 'rejected'
    #         elif approved_count == total_approvers and total_approvers > 0:
    #             new_status = 'approved'
    #         elif approved_count > 0:
    #             new_status = 'partially_approved'
    #         else:
    #             new_status = 'pending'
    #     else:
    #         # Get unique sections
    #         section_ids = all_section_approvals.values_list('section_id', flat=True).distinct()
    #         total_approvers = self.selected_approvers.count()
            
    #         sections_approved = 0
    #         sections_pending = 0
    #         sections_rejected = 0
            
    #         for section_id in section_ids:
    #             section_approvals = all_section_approvals.filter(section_id=section_id)
    #             approved_count = section_approvals.filter(status='approved').count()
    #             rejected_count = section_approvals.filter(status='rejected').count()
                
    #             if total_approvers == 2:
    #                 if rejected_count > 0:
    #                     sections_rejected += 1
    #                 elif approved_count == 2:
    #                     sections_approved += 1
    #                 else:
    #                     sections_pending += 1
    #             else:
    #                 if rejected_count > 0:
    #                     sections_rejected += 1
    #                 elif approved_count == total_approvers:
    #                     sections_approved += 1
    #                 else:
    #                     sections_pending += 1
            
    #         # Determine overall status
    #         if sections_rejected > 0:
    #             new_status = 'rejected'
    #         elif sections_approved > 0 and sections_pending > 0:
    #             new_status = 'partially_approved'  # Some approved, some pending
    #         elif sections_approved > 0 and sections_pending == 0:
    #             new_status = 'approved'  # All sections approved
    #         else:
    #             new_status = 'pending'
        
    #     if self.status != new_status:
    #         self.status = new_status
    #         self.save(update_fields=['status'])
    #         print(f"Updated visitor status to {new_status}")
        
    #     return self.status

    # def update_overall_visitor_status(self):
    #     """
    #     Update the overall visitor status based on section approvals.
    #     Status becomes 'partially_approved' if at least one section is fully approved 
    #     (both approvers approved it), even if other sections are rejected.
    #     """
    #     all_section_approvals = self.visitor_section_approvals.all()
        
    #     if not all_section_approvals.exists():
    #         # No sections - use legacy approval logic
    #         total_approvers = self.selected_approvers.count()
    #         approved_count = self.visitor_approvals.filter(status='approved').count()
    #         rejected_count = self.visitor_approvals.filter(status='rejected').count()
            
    #         if rejected_count > 0:
    #             new_status = 'rejected'
    #         elif approved_count == total_approvers and total_approvers > 0:
    #             new_status = 'approved'
    #         elif approved_count > 0:
    #             new_status = 'partially_approved'
    #         else:
    #             new_status = 'pending'
    #     else:
    #         # Get unique sections
    #         section_ids = all_section_approvals.values_list('section_id', flat=True).distinct()
    #         total_approvers = self.selected_approvers.count()
            
    #         sections_fully_approved = 0  # Both approvers approved
    #         sections_rejected = 0
            
    #         for section_id in section_ids:
    #             section_approvals = all_section_approvals.filter(section_id=section_id)
    #             approved_count = section_approvals.filter(status='approved').count()
    #             rejected_count = section_approvals.filter(status='rejected').count()
                
    #             if total_approvers == 2:
    #                 if rejected_count > 0:
    #                     sections_rejected += 1
    #                 elif approved_count == 2:
    #                     sections_fully_approved += 1
    #             else:
    #                 if rejected_count > 0:
    #                     sections_rejected += 1
    #                 elif approved_count == total_approvers:
    #                     sections_fully_approved += 1
            
    #         # Determine overall status
    #         if sections_fully_approved > 0:
    #             # CRITICAL: If ANY section is fully approved, status is partially_approved
    #             new_status = 'partially_approved'
    #         elif sections_rejected > 0:
    #             new_status = 'rejected'
    #         else:
    #             new_status = 'pending'
        
    #     if self.status != new_status:
    #         self.status = new_status
    #         self.save(update_fields=['status'])
    #         print(f"Updated visitor status to {new_status}")
        
    #     return self.status
    
    def update_overall_visitor_status(self):
        """
        Update the overall visitor status based on section approvals.
        Status becomes:
        - 'approved' if at least ONE section is fully approved (both approvers approved it)
        - 'rejected' if ALL sections are rejected
        - 'pending' if no approvals yet
        - 'partially_approved' for any other case (won't be used with consensus)
        """
        all_section_approvals = self.visitor_section_approvals.all()
        
        if not all_section_approvals.exists():
            # No sections - use legacy approval logic
            total_approvers = self.selected_approvers.count()
            approved_count = self.visitor_approvals.filter(status='approved').count()
            rejected_count = self.visitor_approvals.filter(status='rejected').count()
            
            if rejected_count > 0:
                new_status = 'rejected'
            elif approved_count == total_approvers and total_approvers > 0:
                new_status = 'approved'
            elif approved_count > 0:
                new_status = 'partially_approved'
            else:
                new_status = 'pending'
        else:
            # Get unique sections
            section_ids = all_section_approvals.values_list('section_id', flat=True).distinct()
            total_approvers = self.selected_approvers.count()
            
            sections_fully_approved = 0  # Both approvers approved
            sections_rejected = 0
            
            for section_id in section_ids:
                section_approvals = all_section_approvals.filter(section_id=section_id)
                approved_count = section_approvals.filter(status='approved').count()
                rejected_count = section_approvals.filter(status='rejected').count()
                
                if total_approvers == 2:
                    if rejected_count > 0:
                        sections_rejected += 1
                    elif approved_count == 2:
                        sections_fully_approved += 1
                else:
                    if rejected_count > 0:
                        sections_rejected += 1
                    elif approved_count == total_approvers:
                        sections_fully_approved += 1
            
            # CRITICAL FIX: Determine overall status
            if sections_fully_approved > 0:
                # If ANY section is fully approved, status is 'approved' (not partially_approved)
                new_status = 'approved'
            elif sections_rejected > 0:
                # All sections are rejected
                new_status = 'rejected'
            else:
                # No approvals yet
                new_status = 'pending'
        
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])
            print(f"Updated visitor status from {self.status} to {new_status}")
        
        return self.status

    def check_approval_status(self):
        """Public method to check and update status"""
        return self.update_overall_visitor_status()





class VisitorSectionTracking(models.Model):
    """Track check-in/check-out times for each section per visitor"""
    
    STATUS_CHOICES = [
        ('pending', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]
    
    visitor = models.ForeignKey('account.Visitor', on_delete=models.CASCADE, related_name='section_trackings')
    section = models.ForeignKey('account.Section', on_delete=models.CASCADE, related_name='visitor_trackings')
    
    # Section visit times
    section_check_in = models.DateTimeField(null=True, blank=True, db_index=True)
    section_check_out = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Duration tracking (auto-calculated)
    duration_minutes = models.IntegerField(default=0, help_text="Time spent in this section in minutes")
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Security personnel who performed actions
    checked_in_by = models.ForeignKey(
        'account.Employee', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='section_checkins'
    )
    checked_out_by = models.ForeignKey(
        'account.Employee', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='section_checkouts'
    )
    
    # Notes
    check_in_notes = models.TextField(blank=True)
    check_out_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['visitor', 'section']
        ordering = ['section__name']
        indexes = [
            models.Index(fields=['visitor', 'status']),
            models.Index(fields=['section_check_in']),
            models.Index(fields=['section_check_out']),
        ]
    
    def save(self, *args, **kwargs):
        # Calculate duration if both times exist
        if self.section_check_in and self.section_check_out:
            if self.section_check_out > self.section_check_in:
                duration = self.section_check_out - self.section_check_in
                self.duration_minutes = int(duration.total_seconds() / 60)
        
        # Update status based on times
        if self.section_check_in and self.section_check_out:
            self.status = 'completed'
        elif self.section_check_in:
            self.status = 'in_progress'
        else:
            self.status = 'pending'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.visitor.full_name} - {self.section.name} - {self.status}"

