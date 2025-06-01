# logs/admin.py
from django.contrib import admin
from .models import ActivityLog

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'note', 'related_model', 'related_id', 'account')
    search_fields = ('note', 'user__username')
    list_filter = ('timestamp', 'user')
