"""Role-based permissions, enforced in the API (not only by hiding buttons in the UI)."""
from rest_framework.permissions import BasePermission

from .models import User


class HasRole(BasePermission):
    roles = ()
    message = "Bạn không có quyền thực hiện thao tác này."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.role in self.roles)


class IsAdminRole(HasRole):
    roles = (User.Role.ADMIN,)


class IsRescueTeam(HasRole):
    roles = (User.Role.RESCUE_TEAM,)


class IsCitizen(HasRole):
    roles = (User.Role.CITIZEN,)
