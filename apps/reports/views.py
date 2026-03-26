from django.utils import timezone
from rest_framework.views import APIView

from apps.batches.models import Batch
from apps.products.models import Product
from apps.schedule.models import TestPoint
from core.permissions import IsAnalystOrAbove
from core.responses import success_response


class DashboardView(APIView):
    """
    GET /api/v1/reports/dashboard/
    Returns all data needed by the frontend dashboard in a single call.
    Authenticated users only — all roles can see the dashboard.
    """

    permission_classes = [IsAnalystOrAbove]

    def get(self, request):
        today = timezone.now().date()
        in_30_days = today + timezone.timedelta(days=30)

        # ==================== Counts ====================
        total_products = Product.objects.count()
        active_batches = Batch.objects.filter(status="active").count()
        overdue_count = TestPoint.objects.filter(status="overdue").count()
        upcoming_count = TestPoint.objects.filter(
            status="pending",
            scheduled_date__gte=today,
            scheduled_date__lte=in_30_days,
        ).count()

        # ==================== Overdue test points  ====================
        overdue_points = (
            TestPoint.objects.filter(status="overdue")
            .select_related("batch", "batch__product")
            .order_by("scheduled_date")[:20]
        )

        # ==================== Upcoming test points (next 30 days)  ====================
        upcoming_points = (
            TestPoint.objects.filter(
                status="pending",
                scheduled_date__gte=today,
                scheduled_date__lte=in_30_days,
            )
            .select_related("batch", "batch__product")
            .order_by("scheduled_date")[:20]
        )
        # ==================== Failed batches ====================
        failed_batches = (
            Batch.objects.filter(status="failed")
            .select_related("product")
            .order_by("-updated_at")[:10]
        )

        # ==================== Active batches in chamber ====================
        active_batches_list = (
            Batch.objects.filter(status="active")
            .select_related("product")
            .order_by("-created_at")[:10]
        )

        return success_response(
            data={
                "summary": {
                    "total_products": total_products,
                    "active_batches": active_batches,
                    "overdue_tests": overdue_count,
                    "upcoming_tests": upcoming_count,
                },
                "overdue_test_points": [
                    {
                        "id": str(tp.id),
                        "batch_number": tp.batch.batch_number,
                        "product_name": tp.batch.product.name,
                        "month": tp.month,
                        "scheduled_date": str(tp.scheduled_date),
                        "status": tp.status,
                    }
                    for tp in overdue_points
                ],
                "upcoming_test_points": [
                    {
                        "id": str(tp.id),
                        "batch_number": tp.batch.batch_number,
                        "product_name": tp.batch.product.name,
                        "month": tp.month,
                        "scheduled_date": str(tp.scheduled_date),
                        "status": tp.status,
                    }
                    for tp in upcoming_points
                ],
                "failed_batches": [
                    {
                        "id": str(b.id),
                        "batch_number": b.batch_number,
                        "product_name": b.product.name,
                        "study_type": b.study_type,
                        "status": b.status,
                    }
                    for b in failed_batches
                ],
                "active_batches": [
                    {
                        "id": str(b.id),
                        "batch_number": b.batch_number,
                        "product_name": b.product.name,
                        "study_type": b.study_type,
                        "location": b.get_location(),
                        "qty_remaining": b.qty_remaining,
                    }
                    for b in active_batches_list
                ],
            }
        )
