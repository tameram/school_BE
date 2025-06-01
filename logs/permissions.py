# logs/permissions.py
from rest_framework.permissions import BasePermission

class IsManagerUser(BasePermission):
    """
    Allows access only to users with role = 'manager'.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'manager'
