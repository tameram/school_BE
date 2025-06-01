from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Employee, EmployeeHistory
from .serializers import EmployeeSerializer, EmployeeHistorySerializer
from logs.utils import log_activity


class EmployeeListCreateView(generics.ListCreateAPIView):
    serializer_class = EmployeeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee_type']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Employee.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إنشاء الموظف {instance.first_name} {instance.last_name}",
            related_model='Employee',
            related_id=str(instance.id)
        )


class EmployeeRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Employee.objects.filter(account=self.request.user.account)

    def perform_update(self, serializer):
        instance = serializer.save(account=self.request.user.account)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم تعديل بيانات الموظف {instance.first_name} {instance.last_name}",
            related_model='Employee',
            related_id=str(instance.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف الموظف {instance.first_name} {instance.last_name}",
            related_model='Employee',
            related_id=str(instance.id)
        )
        instance.delete()


class EmployeeHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeHistorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmployeeHistory.objects.filter(employee__account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إضافة سجل للموظف {instance.employee.first_name} {instance.employee.last_name} - {instance.event}",
            related_model='EmployeeHistory',
            related_id=str(instance.id)
        )
