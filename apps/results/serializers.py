from rest_framework import serializers
from apps.results.models import TestResult
from apps.schedule.models import TestPoint
from core.exceptions import ResultAlreadySubmitted
from services.outcome_evaluator import OutcomeEvaluator


class TestResultSerializer(serializers.ModelSerializer):
    analyst_name = serializers.SerializerMethodField()
    test_name = serializers.SerializerMethodField()

    class Meta:
        model = TestResult
        fields = [
            "id",
            "test_point",
            "monograph_test",
            "test_name",
            "value",
            "unit",
            "specification_snapshot",
            "pass_fail",
            "analyst",
            "analyst_name",
            "submitted_at",
            "notes",
        ]
        read_only_fields = [
            "id",
            "specification_snapshot",
            "pass_fail",
            "analyst",
            "submitted_at",
        ]

    def get_analyst_name(self, obj):
        if obj.analyst:
            return obj.analyst.full_name
        return None

    def get_test_name(self, obj):
        return obj.monograph_test.name

    def validate(self, data):
        test_point = data.get("test_point")
        monograph_test = data.get("monograph_test")

        # Check for duplicate result
        if test_point and monograph_test:
            if TestResult.objects.filter(
                test_point=test_point,
                monograph_test=monograph_test,
            ).exists():
                raise ResultAlreadySubmitted()

        return data

    def create(self, validated_data):
        from django.db import transaction
        from django.utils import timezone

        monograph_test = validated_data["monograph_test"]
        test_point = validated_data["test_point"]

        # Snapshot the specification at time of submission
        validated_data["specification_snapshot"] = monograph_test.specification

        # Auto-calculate pass/fail
        validated_data["pass_fail"] = OutcomeEvaluator.evaluate(
            validated_data["value"],
            monograph_test.specification,
        )

        with transaction.atomic():
            result = TestResult.objects.create(**validated_data)

            # Check if all tests for this test point are now complete
            monograph = test_point.batch.product.monograph
            total_tests = monograph.tests.count()
            submitted_results = TestResult.objects.filter(test_point=test_point).count()

            if submitted_results >= total_tests:
                # Check if any result failed
                has_failure = TestResult.objects.filter(
                    test_point=test_point,
                    pass_fail="fail",
                ).exists()

                test_point.status = "failed" if has_failure else "completed"
                test_point.completed_at = timezone.now()
                test_point.save(update_fields=["status", "completed_at", "updated_at"])

        return result
