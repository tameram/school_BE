# logs/views.py
from rest_framework import generics, permissions
from .models import ActivityLog
from .serializers import ActivityLogSerializer
from .permissions import IsManagerUser

class ActivityLogListView(generics.ListAPIView):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsManagerUser]

    def get_queryset(self):
        return ActivityLog.objects.filter(account=self.request.user.account).order_by('-timestamp')

