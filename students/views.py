from rest_framework import generics
from .models import Student, SchoolClass, StudentHistory, Bus
from rest_framework.generics import RetrieveUpdateAPIView
from .serializers import StudentSerializer, SchoolClassListSerializer, SchoolClassDetailSerializer, StudentHistorySerializer, BusSerializer, BusCreateSerializer
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from datetime import date

def get_serializer_class(self):
    if self.request.method == 'POST':
        return BusCreateSerializer
    return BusSerializer
class BusListCreateView(generics.ListCreateAPIView):
    queryset = Bus.objects.select_related('driver').all()

    def perform_create(self, serializer):
        serializer.save(
            account=self.request.user.account,
            created_by=self.request.user
        )

    def get_queryset(self):
        return Bus.objects.filter(account=self.request.user.account)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BusCreateSerializer
        return BusSerializer

class BusRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Bus.objects.filter(account=self.request.user.account)

    def perform_update(self, serializer):
        serializer.save(account=self.request.user.account)

class StudentListCreateView(generics.ListCreateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_archived', 'account']
    ordering_fields = ['date_of_registration']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Student.objects.filter(account_id=self.request.user.account_id)

    def perform_create(self, serializer):
        serializer.save(account=self.request.user.account)

class StudentRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Student.objects.all()
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

        # Save the updated student
        updated_student = serializer.save(account=self.request.user.account)

        # Log history if class changed
        if old_class != updated_student.school_class:
            StudentHistory.objects.create(
                student=updated_student,
                event="تغيير الصف",
                note=f"تم نقل الطالب من الصف '{old_class}' إلى الصف '{updated_student.school_class}'",
                date=date.today()
            )

        # Log history if bus changed
        if old_bus != updated_student.bus or old_bus_join != updated_student.is_bus_joined:
            if updated_student.is_bus_joined:
                StudentHistory.objects.create(
                    student=updated_student,
                    event="تحديث باص المدرسة",
                    note=f"تم تعيين الباص '{updated_student.bus}' للطالب",
                    date=date.today()
                )
            else:
                StudentHistory.objects.create(
                    student=updated_student,
                    event="إلغاء الالتحاق بالباص",
                    note="تم إزالة الطالب من الباص",
                    date=date.today()
                )


class SchoolClassCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'teacher']

class SchoolClassListCreateView(generics.ListCreateAPIView):
    queryset = SchoolClass.objects.all()

    def get_queryset(self):
        return SchoolClass.objects.filter(account=self.request.user.account)
    
    def perform_create(self, serializer):
        serializer.save(
            account=self.request.user.account,
            created_by=self.request.user
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SchoolClassCreateSerializer
        return SchoolClassListSerializer

class SchoolClassRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassDetailSerializer
    lookup_field = 'id'

class StudentHistoryListCreateView(generics.ListCreateAPIView):
    queryset = StudentHistory.objects.all()
    serializer_class = StudentHistorySerializer

    def get_queryset(self):
        return StudentHistory.objects.filter(student__account=self.request.user.account)

class StudentHistoryDetailView(generics.RetrieveAPIView):
    queryset = StudentHistory.objects.all()
    serializer_class = StudentHistorySerializer
    lookup_field = 'id'