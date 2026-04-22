from rest_framework import permissions

class IsEmployee(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # For visitor objects, allow if user created it or is an approver
        if hasattr(obj, 'created_by'):
            return (obj.created_by == request.user or 
                    obj.selected_approvers.filter(id=request.user.id).exists())
        return True