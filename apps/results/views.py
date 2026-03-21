from rest_framework.views import APIView
from rest_framework import status

from apps.results.models import TestResult
from apps.results.serializers import TestResultSerializer
from core.permissions import IsAnalystOrAbove, HasValidSignature
from core.responses import success_response, error_response
from services.audit_service import AuditService


class TestResultListCreateView(APIView):
    """
    GET  /api/v1/results/         — list results
    POST /api/v1/results/         — submit a new result (requires e-signature)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAnalystOrAbove(), HasValidSignature()]
        return [IsAnalystOrAbove()]

    def get(self, request):
        queryset = TestResult.objects.select_related(
            "test_point", "monograph_test", "analyst"
        ).all()

        test_point_id = request.query_params.get("test_point")
        pass_fail = request.query_params.get("pass_fail")

        if test_point_id:
            queryset = queryset.filter(test_point__id=test_point_id)
        if pass_fail:
            queryset = queryset.filter(pass_fail=pass_fail)

        return success_response(data=TestResultSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = TestResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save(analyst=request.user)

        AuditService.log(
            performed_by=request.user,
            action="CREATE",
            model_name="TestResult",
            object_id=result.id,
            object_repr=str(result),
            new_value={
                "value": result.value,
                "pass_fail": result.pass_fail,
                "specification": result.specification_snapshot,
            },
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return success_response(
            data=TestResultSerializer(result).data,
            status_code=status.HTTP_201_CREATED,
        )


class TestResultDetailView(APIView):
    """
    GET /api/v1/results/<id>/  — get single result
    """

    permission_classes = [IsAnalystOrAbove]

    def get(self, request, pk):
        try:
            result = TestResult.objects.select_related(
                "test_point", "monograph_test", "analyst"
            ).get(pk=pk)
        except TestResult.DoesNotExist:
            return error_response(
                {"detail": "Result not found."},
                status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=TestResultSerializer(result).data)


class SignatureVerifyView(APIView):
    """
    POST /api/v1/results/signature/verify/
    Re-authenticates the analyst and issues a short-lived
    signature token stored in Redis.

    The analyst must call this before submitting results.
    The token is valid for 5 minutes.
    """

    permission_classes = [IsAnalystOrAbove]

    def post(self, request):
        import uuid
        from django.core.cache import cache

        password = request.data.get("password")
        if not password:
            return error_response(
                {"password": ["This field is required."]},
                status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.check_password(password):
            request.user.increment_failed_attempts()
            from core.exceptions import SignatureFailedError

            raise SignatureFailedError()

        request.user.reset_failed_attempts()

        # Generate signature token and store in Redis for 5 minutes
        token = str(uuid.uuid4())
        cache_key = f"sig_token:{request.user.id}:{token}"
        cache.set(cache_key, True, timeout=300)

        AuditService.log(
            performed_by=request.user,
            action="SIGN",
            model_name="CustomUser",
            object_id=request.user.id,
            object_repr=str(request.user),
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return success_response(
            data={"signature_token": token},
            message="Signature verified. Token valid for 5 minutes.",
        )
