from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from students.models import Student
from .models import EmployeeType, AuthorizedPayer, SchoolFee, SchoolYear
from .serializers import EmployeeTypeSerializer, AuthorizedPayerSerializer, SchoolFeeSerializer, SchoolYearSerializer
from logs.utils import log_activity
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, F, ExpressionWrapper, DecimalField



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
        return SchoolYear.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
    # 1. Create the new school year
        school_year = serializer.save(account=self.request.user.account, created_by=self.request.user)

        # 2. Get the default school fee
        default_fee = SchoolFee.objects.filter(
            account=self.request.user.account,
            school_class__isnull=True,
            student__isnull=True
        ).first()

        if not default_fee:
            return  # No default to apply

        # 3. Get all non-archived students
        students = Student.objects.filter(account=self.request.user.account, is_archived=False)

        # 4. Bulk create school fee records for those students
        fees_to_create = []
        for student in students:
            fees_to_create.append(SchoolFee(
                student=student,
                school_year=school_year,
                school_fee=default_fee.school_fee,
                books_fee=default_fee.books_fee,
                trans_fee=default_fee.trans_fee,
                clothes_fee=default_fee.clothes_fee,
                account=self.request.user.account,
                created_by=self.request.user
            ))

        SchoolFee.objects.bulk_create(fees_to_create)

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

    @action(detail=False, methods=['get'], url_path='current-year-total')
    def current_year_total(self, request):
        account = request.user.account

        active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
        if not active_year:
            return Response({"detail": "لا يوجد سنة دراسية مفعلة حالياً"}, status=404)

        # Get non-archived student IDs
        student_ids = Student.objects.filter(is_archived=False).values_list('id', flat=True)

        # Expression to calculate total fee per row
        total_fee_expr = ExpressionWrapper(
            F('school_fee') + F('books_fee') + F('trans_fee') + F('clothes_fee'),
            output_field=DecimalField()
        )

        # Filter fees and sum total of all rows
        total = (
            SchoolFee.objects
            .filter(account=account, school_year=active_year, student__in=student_ids)
            .annotate(total_fee=total_fee_expr)
            .aggregate(total_sum=Sum('total_fee'))
        )

        return Response({"total_school_fees": total['total_sum'] or 0})

    @action(detail=False, methods=['get', 'put'], url_path='default')
    def default_fee(self, request):
        if request.method == 'GET':
            try:
                fee = SchoolFee.objects.get(
                    account=request.user.account, 
                    school_class__isnull=True, 
                    student__isnull=True
                )
                serializer = self.get_serializer(fee)
                return Response(serializer.data)
            except SchoolFee.DoesNotExist:
                # Return default values with zeros instead of 404
                default_data = {
                    'id': None,
                    'school_fee': 0.00,
                    'books_fee': 0.00,
                    'trans_fee': 0.00,
                    'clothes_fee': 0.00,
                    'school_class': None,
                    'student': None,
                    'school_year': None,
                    'created_at': None,
                    'year': None
                }
                return Response(default_data, status=status.HTTP_200_OK)
        
        if request.method == 'PUT':
            fee, created = SchoolFee.objects.get_or_create(
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
                    note="تم تعديل الرسوم الافتراضية" if not created else "تم إنشاء الرسوم الافتراضية",
                    related_model='SchoolFee',
                    related_id=str(updated.id)
                )
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


