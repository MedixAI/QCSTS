from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsAnalystOrAbove
from core.responses import success_response, error_response
from apps.results.models import TestResult
from apps.schedule.models import TestPoint
from apps.products.models import MonographTest
from services.signature_service import SignatureService
from services.outcome_evaluator import OutcomeEvaluator


class VerifySignatureView(APIView):
    """
    POST /api/v1/results/signature/verify/
    Body: { "password": "user_password" }
    Returns: { "signature_token": "uuid" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = request.data.get('password')
        user = request.user

        if not user.check_password(password):
            return error_response("Invalid password", status=401)

        token = SignatureService.issue(user)
        return success_response({"signature_token": token})


class SubmitResultView(APIView):
    """
    POST /api/v1/results/
    Header: X-Signature-Token: <token>
    Body: {
        "test_point": "uuid",
        "monograph_test": "uuid",
        "value": "99.5",
        "unit": "%",
        "notes": "optional"
    }
    """
    permission_classes = [IsAuthenticated, IsAnalystOrAbove]

    def post(self, request):
        token = request.headers.get('X-Signature-Token')
        if not token or not SignatureService.validate(request.user, token):
            return error_response("Invalid or missing signature token", status=401)

        test_point_id = request.data.get('test_point')
        monograph_test_id = request.data.get('monograph_test')
        value = request.data.get('value')
        unit = request.data.get('unit', '')
        notes = request.data.get('notes', '')

        if not all([test_point_id, monograph_test_id, value]):
            return error_response("Missing required fields", status=400)

        try:
            test_point = TestPoint.objects.get(id=test_point_id)
            monograph_test = MonographTest.objects.get(id=monograph_test_id)
        except Exception:
            return error_response("Invalid test_point or monograph_test", status=404)

        if TestResult.objects.filter(test_point=test_point, monograph_test=monograph_test).exists():
            return error_response("Result already submitted for this test point", status=409)

        specification = monograph_test.specification
        pass_fail = OutcomeEvaluator.evaluate(value, specification)

        result = TestResult.objects.create(
            test_point=test_point,
            monograph_test=monograph_test,
            value=value,
            unit=unit,
            specification_snapshot=specification,
            pass_fail=pass_fail,
            analyst=request.user,
            notes=notes,
        )

        # This will update test point status and batch status
        test_point.update_status()

        return success_response({
            "id": str(result.id),
            "test_name": monograph_test.name,
            "value": result.value,
            "unit": result.unit,
            "pass_fail": result.pass_fail,
            "submitted_at": result.submitted_at.isoformat(),
        })