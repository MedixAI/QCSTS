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
        return obj.analyst.full_name if obj.analyst else None

    def get_test_name(self, obj):
        return obj.monograph_test.name

    def validate(self, data):
        test_point = data.get("test_point")
        monograph_test = data.get("monograph_test")
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

        validated_data["specification_snapshot"] = monograph_test.specification
        validated_data["pass_fail"] = OutcomeEvaluator.evaluate(
            validated_data["value"],
            monograph_test.specification,
        )

        with transaction.atomic():
            result = TestResult.objects.create(**validated_data)
            # Update test point status
            test_point.update_status()

            # After updating test point, update batch status
            batch = test_point.batch
            all_tps = batch.test_points.all()
            completed_count = all_tps.filter(status="completed").count()
            failed_count = all_tps.filter(status="failed").count()

            if completed_count == all_tps.count():
                batch.status = "complete"
                batch.save(update_fields=["status", "updated_at"])
            elif failed_count > 0:
                batch.status = "failed"
                batch.save(update_fields=["status", "updated_at"])

        return result