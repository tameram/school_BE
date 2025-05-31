from rest_framework import generics
from .models import Student, SchoolClass, StudentHistory, Bus
from .serializers import StudentSerializer, SchoolClassListSerializer, SchoolClassDetailSerializer, StudentHistorySerializer, BusSerializer, BusCreateSerializer
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from datetime import date

def get_serializer_class(self):
    if self.request.method == 'POST':
        return BusCreateSerializer
    return BusSerializer
class BusListCreateView(generics.ListCreateAPIView):
    queryset = Bus.objects.select_related('driver').all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BusCreateSerializer
        return BusSerializer

class BusRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    lookup_field = 'id'

class StudentListCreateView(generics.ListCreateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_archived', 'account']
    ordering_fields = ['date_of_registration']

class StudentRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    lookup_field = 'id'

    def perform_update(self, serializer):
        student = self.get_object()
        old_class = student.school_class
        old_bus = student.bus
        old_bus_join = student.is_bus_joined

        # Save the updated student
        updated_student = serializer.save()

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

class StudentHistoryDetailView(generics.RetrieveAPIView):
    queryset = StudentHistory.objects.all()
    serializer_class = StudentHistorySerializer
    lookup_field = 'id'