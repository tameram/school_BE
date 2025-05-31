from rest_framework import serializers

from payments.serializers import PaymentSerializer, RecipientSerializer
from .models import Student, SchoolClass, StudentHistory, Bus
from rest_framework import generics
from payments.models import Recipient
from settings_data.serializers import SchoolFeeSerializer
from settings_data.models import SchoolFee


class StudentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentHistory
        fields = ['id', 'event', 'note', 'date']
class StudentSerializer(serializers.ModelSerializer):
    history = StudentHistorySerializer(many=True, read_only=True)
    recipients = RecipientSerializer(many=True, read_only=True, source='recipient_set')
    school_fees = serializers.SerializerMethodField()
    class Meta:
        model = Student
        fields = '__all__'

    def validate_student_id(self, value):
        if not value:
            return value  # Allow blank or null

        # Create case
        if not self.instance:
            if Student.objects.filter(student_id=value).exists():
                raise serializers.ValidationError("هذا الطالب موجود بالفعل في النظام")
        else:
            # Update case
            if Student.objects.filter(student_id=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("هذا الطالب موجود بالفعل في النظام")
        return value
    
    def get_school_fees(self, obj):
        # Get distinct SchoolFee objects linked via Recipient
        fees = SchoolFee.objects.filter(recipient__student=obj).distinct()
        return SchoolFeeSerializer(fees, many=True).data




class StudentBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'first_name', 'second_name', 'student_id', 'school_class']

class BusSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()
    driver_name = serializers.SerializerMethodField()
    students = StudentBasicSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Bus
        fields = [
            'id', 'name', 'bus_number', 'bus_type',
            'capacity', 'phone_number', 'manager_name',
            'student_count', 'driver_name', 'students' ,
            'payments'
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