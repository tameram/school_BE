from rest_framework import generics, serializers
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from datetime import date

from .models import Student, SchoolClass, StudentHistory, Bus
from .serializers import (
    StudentSerializer, SchoolClassListSerializer, SchoolClassDetailSerializer,
    StudentHistorySerializer, BusSerializer, BusCreateSerializer
)
from logs.utils import log_activity


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
        return SchoolClassCreateSerializer if self.request.method == 'POST' else SchoolClassListSerializer


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
