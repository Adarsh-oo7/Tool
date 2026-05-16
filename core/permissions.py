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