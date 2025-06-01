# logs/models.py
from django.db import models
from django.conf import settings

class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs'
    )
    note = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    related_model = models.CharField(max_length=100, blank=True, null=True)
    related_id = models.CharField(max_length=100, blank=True, null=True)

    account = models.ForeignKey("users.Account", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user} - {self.note[:40]} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
