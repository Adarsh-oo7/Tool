from rest_framework.exceptions import PermissionDenied


class BranchScopedMixin:
    """
    Automatically scopes queryset to request.user.branch for non-owner roles.
    The ViewSet must define `branch_field` (default: 'branch') if the FK
    to Branch has a different name on the model.
    """
    branch_field = 'branch'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'owner':
            return qs
        if user.branch is None:
            return qs.none()
        return qs.filter(**{self.branch_field: user.branch})


class UserScopedMixin:
    """
    Scopes queryset to objects belonging to request.user only.
    Use for models that have a direct FK to the user (e.g. Attendance, Notification).
    """
    user_field = 'user'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role in ('owner', 'manager'):
            # Managers/owners can see their branch's data — further filtered by view
            return qs
        return qs.filter(**{self.user_field: user})
