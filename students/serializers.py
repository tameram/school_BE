from rest_framework import serializers
from .models import Student, SchoolClass, StudentHistory, Bus
from rest_framework import generics


class StudentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentHistory
        fields = ['id', 'event', 'note', 'date']
class StudentSerializer(serializers.ModelSerializer):
    history = StudentHistorySerializer(many=True, read_only=True)
    class Meta:
        model = Student
        fields = '__all__'

class BusSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()
    driver_name = serializers.SerializerMethodField()  # ✅ Add this line

    class Meta:
        model = Bus
        fields = [
            'id', 'name', 'bus_number', 'bus_type',
            'capacity', 'phone_number', 'manager_name',
            'student_count', 'driver_name'
        ]

    def get_student_count(self, obj):
        return obj.students.count()

    def get_driver_name(self, obj):
        if obj.driver:
            print("✅ Driver found:", obj.driver.first_name, obj.driver.last_name)
            return f"{obj.driver.first_name} {obj.driver.last_name}".strip()
        print("❌ Driver is None for Bus:", obj.id)
        return "غير محدد"

class SchoolClassListSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()
    teacher = serializers.SerializerMethodField()

    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'student_count', 'teacher']

    def get_student_count(self, obj):
        return obj.students.count()

    def get_teacher(self, obj):
        if obj.teacher:
            return f"{obj.teacher.first_name} {obj.teacher.last_name}".strip()
        return "غير محدد"

class SchoolClassDetailSerializer(serializers.ModelSerializer):
    students = StudentSerializer(many=True, read_only=True)

    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'students']


class BusCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = [
            'id', 'name', 'bus_number', 'bus_type',
            'capacity', 'phone_number', 'manager_name', 'driver'
        ]

class SchoolClassRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):  # ✅ allow DELETE
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassDetailSerializer
    lookup_field = 'id'