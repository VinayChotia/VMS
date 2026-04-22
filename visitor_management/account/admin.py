from django.contrib import admin
from .models import Employee, Visitor, VisitorApproval

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'department', 'is_available']
    search_fields = ['email', 'full_name']

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'status', 'created_by', 'created_at']
    list_filter = ['status']
    search_fields = ['full_name', 'email']

@admin.register(VisitorApproval)
class VisitorApprovalAdmin(admin.ModelAdmin):
    list_display = ['visitor', 'approver', 'status', 'responded_at']