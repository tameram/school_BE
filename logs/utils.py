# logs/utils.py
from .models import ActivityLog

def log_activity(user, account, note, related_model=None, related_id=None):
    ActivityLog.objects.create(
        user=user,
        account=account,
        note=note,
        related_model=related_model,
        related_id=related_id,
    )
