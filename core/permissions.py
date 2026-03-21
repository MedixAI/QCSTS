from rest_framework.permissions import BasePermission


class IsViewer(BasePermission):
    """Authenticated users with any role. Read-only operations."""

    message = "Authentication required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAnalystOrAbove(BasePermission):
    """
    analyst, reviewer, qa_manager, admin.
    Required for: submitting test results, recording sample pulls.
    """

    message = "Analyst role or above is required for this action."
    ALLOWED_ROLES = {"analyst", "reviewer", "qa_manager", "admin"}

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )


class IsReviewerOrAbove(BasePermission):
    """
    reviewer, qa_manager, admin.
    Required for: counter-signing test results.
    """

    message = "Reviewer role or above is required for this action."
    ALLOWED_ROLES = {"reviewer", "qa_manager", "admin"}

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )


class IsQAManager(BasePermission):
    """
    qa_manager, admin.
    Required for: approving monographs, accessing full audit trail.
    """

    message = "QA Manager role or above is required for this action."
    ALLOWED_ROLES = {"qa_manager", "admin"}

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )


class IsAdmin(BasePermission):
    """
    admin only.
    Required for: user management, system backup, configuration.
    """

    message = "Administrator role is required for this action."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == "admin"


class HasValidSignature(BasePermission):
    """
    Checks that the request includes a valid, non-expired SignatureToken.
    Applied exclusively to result submission endpoints.

    The client must:
    1. Call POST /api/v1/auth/signature/verify/ with password
    2. Receive a signature_token UUID
    3. Include it in the header: X-Signature-Token: <uuid>

    SignatureService stores the token in Redis with 5-minute TTL.
    This permission class checks Redis for that token.
    """

    message = "A valid electronic signature is required. Please verify your identity."

    def has_permission(self, request, view):
        from django.core.cache import cache

        if not (request.user and request.user.is_authenticated):
            return False

        token = request.headers.get("X-Signature-Token")
        if not token:
            return False

        # Check Redis — key format: sig_token:{user_id}:{token}
        cache_key = f"sig_token:{request.user.id}:{token}"
        return cache.get(cache_key) is not None
