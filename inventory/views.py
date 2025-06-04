# inventory/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import StoreItem
from .serializers import StoreItemSerializer
from logs.utils import log_activity

class StoreItemViewSet(viewsets.ModelViewSet):
    serializer_class = StoreItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return StoreItem.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إضافة صنف جديد: {instance.name}",
            related_model='StoreItem',
            related_id=str(instance.id)
        )

    def perform_update(self, serializer):
        instance = serializer.save(account=self.request.user.account)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم تعديل كمية الصنف: {instance.name} إلى {instance.count}",
            related_model='StoreItem',
            related_id=str(instance.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف الصنف: {instance.name}",
            related_model='StoreItem',
            related_id=str(instance.id)
        )
        instance.delete()
