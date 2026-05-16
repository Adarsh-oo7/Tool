from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.user.role in ["owner", "admin"] or request.user.is_superuser))

class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.user.role in ["owner", "admin", "manager", "sub_manager"] or request.user.is_superuser))

class IsStaffOrAbove(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role in ["owner", "admin", "manager", "sub_manager", "staff", "telecaller", "field_staff", "custom"])

class IsTelecaller(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role in ["owner", "admin", "manager", "sub_manager", "staff", "telecaller"])

class IsFieldStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role in ["owner", "admin", "manager", "sub_manager", "staff", "field_staff"])


class HasDynamicPermission(BasePermission):
    """
    Checks if the user has a specific permission string.
    The ViewSet should define a 'permission_map' attribute.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.role == 'owner':
            return True
            
        perm_map = getattr(view, 'permission_map', {})
        required_perm = perm_map.get(view.action)
        
        if required_perm:
            return request.user.has_permission(required_perm)
        return True