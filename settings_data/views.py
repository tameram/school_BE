from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import EmployeeType, AuthorizedPayer, SchoolFee, SchoolYear
from .serializers import EmployeeTypeSerializer, AuthorizedPayerSerializer, SchoolFeeSerializer, SchoolYearSerializer
from logs.utils import log_activity
from rest_framework.permissions import IsAuthenticated


class EmployeeTypeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeType.objects.all()
    serializer_class = EmployeeTypeSerializer

    def get_queryset(self):
        return EmployeeType.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إضافة نوع موظف: {instance.name}",
            related_model='EmployeeType',
            related_id=str(instance.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف نوع الموظف: {instance.name}",
            related_model='EmployeeType',
            related_id=str(instance.id)
        )
        instance.delete()


class AuthorizedPayerViewSet(viewsets.ModelViewSet):
    queryset = AuthorizedPayer.objects.all()
    serializer_class = AuthorizedPayerSerializer

    def get_queryset(self):
        return AuthorizedPayer.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إضافة دافع معتمد: {instance.name}",
            related_model='AuthorizedPayer',
            related_id=str(instance.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف الدافع المعتمد: {instance.name}",
            related_model='AuthorizedPayer',
            related_id=str(instance.id)
        )
        instance.delete()

class SchoolYearViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolYearSerializer
    permission_classes = [IsAuthenticated]
    queryset = SchoolYear.objects.all()
    def get_queryset(self):
        return SchoolYear.objects.filter(account=self.request.user.account, is_active=True)

    def perform_create(self, serializer):
        serializer.save(account=self.request.user.account, created_by=self.request.user)

    @action(detail=False, methods=['patch'], url_path='deactivate')
    def deactivate_all(self, request):
        SchoolYear.objects.filter(account=request.user.account, is_active=True).update(is_active=False)
        return Response({"detail": "Deactivated previous active years"})


class SchoolFeeViewSet(viewsets.ModelViewSet):
    queryset = SchoolFee.objects.all()
    serializer_class = SchoolFeeSerializer

    def get_queryset(self):
        return SchoolFee.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note="تم إنشاء رسوم مدرسية",
            related_model='SchoolFee',
            related_id=str(instance.id)
        )

    def perform_update(self, serializer):
        instance = serializer.save(account=self.request.user.account)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note="تم تعديل رسوم مدرسية",
            related_model='SchoolFee',
            related_id=str(instance.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note="تم حذف رسوم مدرسية",
            related_model='SchoolFee',
            related_id=str(instance.id)
        )
        instance.delete()

    @action(detail=False, methods=['get', 'put'], url_path='default')
    def default_fee(self, request):
        if request.method == 'GET':
            try:
                fee = SchoolFee.objects.get(account=request.user.account, school_class__isnull=True, student__isnull=True)
                serializer = self.get_serializer(fee)
                return Response(serializer.data)
            except SchoolFee.DoesNotExist:
                return Response({"detail": "No default fee found."}, status=404)

        if request.method == 'PUT':
            fee, _ = SchoolFee.objects.get_or_create(
                account=request.user.account,
                school_class=None,
                student=None,
                defaults={'created_by': request.user}
            )
            serializer = self.get_serializer(fee, data=request.data)
            if serializer.is_valid():
                updated = serializer.save(account=request.user.account)
                log_activity(
                    user=request.user,
                    account=request.user.account,
                    note="تم تعديل الرسوم الافتراضية",
                    related_model='SchoolFee',
                    related_id=str(updated.id)
                )
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
