from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction

from apps.chamber.models import SamplePull, LocationHistory
from apps.chamber.serializers import (
    SamplePullSerializer,
    LocationHistorySerializer,
    ChangeBatchLocationSerializer,
)
from core.permissions import IsAnalystOrAbove, IsReviewerOrAbove   # use reviewer
from core.responses import success_response, error_response
from services.audit_service import AuditService


class ChamberInventoryView(APIView):
    permission_classes = [IsAnalystOrAbove]
    # ... unchanged ...


class SamplePullListCreateView(APIView):
    permission_classes = [IsAnalystOrAbove]
    # ... unchanged ...


class ChangeBatchLocationView(APIView):
    # CHANGE: from IsAnalystOrAbove to IsReviewerOrAbove
    permission_classes = [IsReviewerOrAbove]

    def post(self, request):
        serializer = ChangeBatchLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        batch = serializer.validated_data["batch"]
        new_shelf = serializer.validated_data["new_shelf"]
        new_rack = serializer.validated_data["new_rack"]
        new_position = serializer.validated_data["new_position"]
        reason = serializer.validated_data.get("reason", "")

        with transaction.atomic():
            location_log = LocationHistory.objects.create(
                batch=batch,
                old_shelf=batch.shelf,
                old_rack=batch.rack,
                old_position=batch.position,
                new_shelf=new_shelf,
                new_rack=new_rack,
                new_position=new_position,
                changed_by=request.user,
                reason=reason,
                created_by=request.user,
            )
            batch.shelf = new_shelf
            batch.rack = new_rack
            batch.position = new_position
            batch.save(update_fields=["shelf", "rack", "position", "updated_at"])

            AuditService.log(
                performed_by=request.user,
                action="UPDATE",
                model_name="Batch",
                object_id=batch.id,
                object_repr=str(batch),
                old_value={"location": f"{location_log.old_shelf}/{location_log.old_rack}/{location_log.old_position}"},
                new_value={"location": batch.get_location()},
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        return success_response(
            data=LocationHistorySerializer(location_log).data,
            status_code=status.HTTP_201_CREATED,
        )



class LocationHistoryView(APIView):
    """
    GET /api/v1/chamber/locations/<batch_id>/
    Returns the full location history for a batch.
    """

    permission_classes = [IsAnalystOrAbove]

    def get(self, request, pk):
        history = LocationHistory.objects.filter(batch__id=pk)
        return success_response(data=LocationHistorySerializer(history, many=True).data)
