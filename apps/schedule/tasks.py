import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def mark_overdue_test_points():
    """
    Runs every day at 06:00 AM via Celery Beat.
    Finds all pending test points whose scheduled_date
    has passed and marks them as overdue.

    Registered in config/celery.py beat_schedule.
    """
    from apps.schedule.models import TestPoint

    today = timezone.now().date()

    overdue_qs = TestPoint.objects.filter(
        status="pending",
        scheduled_date__lt=today,
    )

    count = overdue_qs.count()

    if count > 0:
        overdue_qs.update(status="overdue")
        logger.info("mark_overdue_test_points: marked %d test points as overdue", count)
    else:
        logger.info("mark_overdue_test_points: no overdue test points found")

    return count
