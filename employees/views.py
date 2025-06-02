from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Employee, EmployeeHistory, EmployeeVirtualTransaction
from .serializers import EmployeeSerializer, EmployeeHistorySerializer, EmployeeVirtualTransactionSerializer
from logs.utils import log_activity
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from payments.models import Payment
from payments.serializers import PaymentSerializer


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

class EmployeePaymentCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, employee_id):
        try:
            employee = Employee.objects.get(id=employee_id, account=request.user.account)
        except Employee.DoesNotExist:
            return Response({'detail': 'الموظف غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['recipient_employee'] = str(employee.id)
        data['account'] = str(request.user.account.id)
        data['created_by'] = str(request.user.id)

        serializer = PaymentSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

class EmployeeVirtualTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeVirtualTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'date']

    def get_queryset(self):
        return EmployeeVirtualTransaction.objects.filter(account=self.request.user.account).order_by('-date')

    def perform_create(self, serializer):
        serializer.save(
            account=self.request.user.account,
            created_by=self.request.user
        )

