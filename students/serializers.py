from rest_framework import serializers

from payments.serializers import PaymentSerializer, RecipientSerializer
from .models import Student, SchoolClass, StudentHistory, Bus
from rest_framework import generics
from payments.models import Recipient
from settings_data.serializers import SchoolFeeSerializer
from settings_data.models import SchoolYear, SchoolFee
from django.db import models



class StudentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentHistory
        fields = ['id', 'event', 'note', 'date']
class StudentSerializer(serializers.ModelSerializer):
    history = StudentHistorySerializer(many=True, read_only=True)
    recipients = RecipientSerializer(many=True, read_only=True, source='recipient_set')
    school_fees = serializers.SerializerMethodField()
    school_fees_by_year = serializers.SerializerMethodField()
    payment_summary = serializers.SerializerMethodField()
    class Meta:
        model = Student
        exclude = ['account']  # ✅ This ensures DRF doesn't try to validate it as input
        read_only_fields = ['id']

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
    
    def get_school_fees_by_year(self, student):
        fees = SchoolFee.objects.filter(student=student)
        return [
            {
                "school_fee": f.school_fee,
                "books_fee": f.books_fee,
                "trans_fee": f.trans_fee,
                "clothes_fee": f.clothes_fee,
                "school_year": str(f.school_year.id) if f.school_year else None
            } for f in fees
        ]
    
    def get_payment_summary(self, student):
        active_year = SchoolYear.objects.filter(account=student.account, is_active=True).first()
        if not active_year:
            return None

        # Get total paid in current year
        total_paid = Recipient.objects.filter(
            student=student, school_year=active_year
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        # Get fee for current year
        school_fee = SchoolFee.objects.filter(student=student, school_year=active_year).first()

        # Fallback to class-level or default fee
        if not school_fee and student.school_class:
            school_fee = SchoolFee.objects.filter(school_class=student.school_class, student__isnull=True, school_year=active_year).first()
        if not school_fee:
            school_fee = SchoolFee.objects.filter(school_class__isnull=True, student__isnull=True, school_year=active_year).first()

        total_fee = sum([
            school_fee.school_fee or 0,
            school_fee.books_fee or 0,
            school_fee.trans_fee or 0,
            school_fee.clothes_fee or 0
        ]) if school_fee else 0

        return f"{total_paid}/{total_fee}"
    
    def get_school_fees(self, student):
        fee = SchoolFee.objects.filter(student=student).first()
        if fee:
            return {
                'school_fee': fee.school_fee,
                'books_fee': fee.books_fee,
                'trans_fee': fee.trans_fee,
                'clothes_fee': fee.clothes_fee,
                'id': fee.id
            }

        if student.school_class:
            fee = SchoolFee.objects.filter(student__isnull=True, school_class=student.school_class).first()
            if fee:
                return {
                    'school_fee': fee.school_fee,
                    'books_fee': fee.books_fee,
                    'trans_fee': fee.trans_fee,
                    'clothes_fee': fee.clothes_fee,
                    'id': fee.id
                }

        fee = SchoolFee.objects.filter(student__isnull=True, school_class__isnull=True, account=student.account).first()
        if fee:
            return {
                'school_fee': fee.school_fee,
                'books_fee': fee.books_fee,
                'trans_fee': fee.trans_fee,
                'clothes_fee': fee.clothes_fee,
                'id': fee.id
            }

        return None



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
        read_only_fields = ['id']

class SchoolClassRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):  # ✅ allow DELETE
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassDetailSerializer
    lookup_field = 'id'