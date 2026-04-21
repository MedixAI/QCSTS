from rest_framework.permissions import BasePermission

class IsViewer(BasePermission):
    message = "Authentication required."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

class IsAnalystOrAbove(BasePermission):
    message = "Analyst role or above is required for this action."
    ALLOWED_ROLES = {"analyst", "supervisor", "qa_manager", "admin"}
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )

class IsReviewerOrAbove(BasePermission):
    """
    supervisor, qa_manager, admin.
    Required for: moving batches, exporting reports (backend).
    """
    message = "Supervisor role or above is required for this action."
    ALLOWED_ROLES = {"supervisor", "qa_manager", "admin"}
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )

class IsQAManager(BasePermission):
    message = "QA Manager role or above is required for this action."
    ALLOWED_ROLES = {"qa_manager", "admin"}
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )

class IsAdmin(BasePermission):
    message = "Administrator role is required for this action."
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == "admin"

class HasValidSignature(BasePermission):
    message = "A valid electronic signature is required. Please verify your identity."
    def has_permission(self, request, view):
        from django.core.cache import cache
        if not (request.user and request.user.is_authenticated):
            return False
        token = request.headers.get("X-Signature-Token")
        if not token:
            return False
        cache_key = f"sig_token:{request.user.id}:{token}"
        return cache.get(cache_key) is not None