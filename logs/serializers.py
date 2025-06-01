# logs/serializers.py
from rest_framework import serializers
from .models import ActivityLog

class ActivityLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()  # to show username instead of ID

    class Meta:
        model = ActivityLog
        fields = ['id', 'timestamp', 'user', 'note', 'related_model', 'related_id']
