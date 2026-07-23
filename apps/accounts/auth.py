from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth

from .models import Role


class RoleAuth(JWTAuth):
    """JWT auth that also enforces a role allowlist."""

    allowed_roles: tuple = ()

    def authenticate(self, request, token):
        user = super().authenticate(request, token)
        if user is None:
            return None
        if not user.is_active:
            raise HttpError(403, "Account is disabled.")
        if self.allowed_roles and user.role not in self.allowed_roles:
            raise HttpError(403, "You do not have permission to perform this action.")
        return user


class AnyUserAuth(RoleAuth):
    allowed_roles = ()


class InstructorAuth(RoleAuth):
    allowed_roles = (Role.INSTRUCTOR, Role.ADMIN)


class AdminAuth(RoleAuth):
    allowed_roles = (Role.ADMIN,)


any_user = AnyUserAuth()
instructor = InstructorAuth()
admin = AdminAuth()