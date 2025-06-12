from rest_framework import generics, serializers
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from datetime import date

from .models import Student, SchoolClass, StudentHistory, Bus,StudentPaymentHistory
from .serializers import (
    StudentSerializer, SchoolClassListSerializer, SchoolClassDetailSerializer,
    StudentHistorySerializer, BusSerializer, BusCreateSerializer
)
from logs.utils import log_activity

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from payments.models import Recipient
from settings_data.models import SchoolFee, SchoolYear
from django.db.models import Sum

from decimal import Decimal
from uuid import UUID


class BusListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        return Bus.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        bus = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إنشاء باص جديد: {bus.bus_number}",
            related_model='Bus',
            related_id=str(bus.id)
        )

    def get_serializer_class(self):
        return BusCreateSerializer if self.request.method == 'POST' else BusSerializer


class BusRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BusSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Bus.objects.filter(account=self.request.user.account)

    def perform_update(self, serializer):
        bus = serializer.save(account=self.request.user.account)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم تعديل بيانات الباص {bus.bus_number}",
            related_model='Bus',
            related_id=str(bus.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف الباص {instance.bus_number}",
            related_model='Bus',
            related_id=str(instance.id)
        )
        instance.delete()


class StudentListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_archived', 'account']
    ordering_fields = ['date_of_registration']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Student.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        student = serializer.save(account=self.request.user.account)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إنشاء الطالب {student.first_name} {student.second_name}",
            related_model='Student',
            related_id=str(student.id)
        )


class StudentRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Student.objects.filter(account=self.request.user.account)

    def perform_update(self, serializer):
        student = self.get_object()
        old_class = student.school_class
        old_bus = student.bus
        old_bus_join = student.is_bus_joined

        updated_student = serializer.save(account=self.request.user.account)

        changes = []

        if old_class != updated_student.school_class:
            StudentHistory.objects.create(
                student=updated_student,
                event="تغيير الصف",
                note=f"تم نقل الطالب من الصف '{old_class}' إلى الصف '{updated_student.school_class}'",
                date=date.today()
            )
            changes.append("الصف")

        if old_bus != updated_student.bus or old_bus_join != updated_student.is_bus_joined:
            if updated_student.is_bus_joined:
                StudentHistory.objects.create(
                    student=updated_student,
                    event="تحديث باص المدرسة",
                    note=f"تم تعيين الباص '{updated_student.bus}' للطالب",
                    date=date.today()
                )
                changes.append("الالتحاق بالباص")
            else:
                StudentHistory.objects.create(
                    student=updated_student,
                    event="إلغاء الالتحاق بالباص",
                    note="تم إزالة الطالب من الباص",
                    date=date.today()
                )
                changes.append("إزالة الباص")

        if changes:
            log_activity(
                user=self.request.user,
                account=self.request.user.account,
                note=f"تم تعديل بيانات الطالب {updated_student.first_name} {updated_student.second_name} ({'، '.join(changes)})",
                related_model='Student',
                related_id=str(updated_student.id)
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def students_with_open_accounts(request):
    account = request.user.account
    active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
    if not active_year:
        return Response({"detail": "لا توجد سنة دراسية مفعلة."}, status=status.HTTP_400_BAD_REQUEST)

    students = Student.objects.filter(account=account, is_archived=False)
    open_students = []

    for student in students:
        # Check if student closed account for current year
        is_closed = StudentPaymentHistory.objects.filter(student=student, year=active_year.label).exists()
        if is_closed:
            continue  # skip

        # Calculate total paid
        total_paid = Recipient.objects.filter(student=student, school_year=active_year).aggregate(Sum('amount'))['amount__sum'] or 0

        # Find the applicable fee
        fee = SchoolFee.objects.filter(student=student, school_year=active_year).first()
        if not fee and student.school_class:
            fee = SchoolFee.objects.filter(school_class=student.school_class, student__isnull=True, school_year=active_year).first()
        if not fee:
            fee = SchoolFee.objects.filter(school_class__isnull=True, student__isnull=True, school_year=active_year).first()

        total_fee = sum([
            fee.school_fee or 0,
            fee.books_fee or 0,
            fee.trans_fee or 0,
            fee.clothes_fee or 0,
        ]) if fee else 0

        if total_paid < total_fee:
            open_students.append(student)

    serializer = StudentSerializer(open_students, many=True)
    return Response(serializer.data)

class SchoolClassListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        return SchoolClass.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        class_obj = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إنشاء الصف {class_obj.name}",
            related_model='SchoolClass',
            related_id=str(class_obj.id)
        )

    def get_serializer_class(self):
        return SchoolClassListSerializer if self.request.method == 'POST' else SchoolClassListSerializer


class SchoolClassRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassDetailSerializer
    lookup_field = 'id'


class StudentHistoryListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentHistorySerializer

    def get_queryset(self):
        return StudentHistory.objects.filter(student__account=self.request.user.account)


class StudentHistoryDetailView(generics.RetrieveAPIView):
    queryset = StudentHistory.objects.all()
    serializer_class = StudentHistorySerializer
    lookup_field = 'id'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_student_account(request, id):
    student = Student.objects.get(id=id, account=request.user.account)
    year_label = request.data.get("year")

    # Get or create the school year
    school_year, _ = SchoolYear.objects.get_or_create(
        label=year_label,
        account=request.user.account,
        defaults={'created_by': request.user}
    )

    # Update all current payments to link them with this year
    payments_qs = Recipient.objects.filter(student=student, school_year__isnull=True)
    payments_qs.update(school_year=school_year)

    # Get serialized copy of payments
    payments = list(payments_qs.values())

    for p in payments:
        for k, v in p.items():
            if isinstance(v, UUID):
                p[k] = str(v)
            elif isinstance(v, Decimal):
                p[k] = float(v)

    # Get student-level school fee
    fee = SchoolFee.objects.filter(student=student).first()
    fee_data = None
    if fee:
        fee_data = {
            "school_fee": fee.school_fee,
            "books_fee": fee.books_fee,
            "trans_fee": fee.trans_fee,
            "clothes_fee": fee.clothes_fee,
        }
        fee.delete()

    total_paid = payments_qs.aggregate(Sum("amount"))["amount__sum"] or 0

    # Save to payment history
    StudentPaymentHistory.objects.create(
        student=student,
        year=year_label,
        total_paid=total_paid,
        fees_snapshot=fee_data,
        payments_snapshot=payments,
        created_by=request.user
    )

    return Response({"message": "تم تسكير الحساب بنجاح"}, status=status.HTTP_200_OK)

