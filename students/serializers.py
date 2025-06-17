from rest_framework import serializers

from payments.serializers import PaymentSerializer, RecipientSerializer
from .models import Student, SchoolClass, StudentHistory, Bus
from rest_framework import generics
from payments.models import Recipient
from settings_data.serializers import SchoolFeeSerializer
from settings_data.models import SchoolYear, SchoolFee
from django.db import models
from rest_framework.permissions import IsAuthenticated


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
    attachment_url = serializers.SerializerMethodField()  # For file URL
    
    class Meta:
        model = Student
        exclude = ['account']
        read_only_fields = ['id']

    def validate_student_id(self, value):
        if not value:
            return value

        if not self.instance:
            if Student.objects.filter(student_id=value).exists():
                raise serializers.ValidationError("هذا الطالب موجود بالفعل في النظام")
        else:
            if Student.objects.filter(student_id=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("هذا الطالب موجود بالفعل في النظام")
        return value

    def validate_parent_phone_2(self, value):
        """Validate optional second phone number"""
        if value and not value.startswith('0') or (value and len(value) != 10):
            raise serializers.ValidationError("رقم الهاتف الثاني يجب أن يكون 10 أرقام ويبدأ بـ 0")
        return value

    def get_attachment_url(self, obj):
        """Return the full URL for the attachment file"""
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return None
    
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
            return {'total_paid': 0, 'total_fee': 0}

        total_paid = Recipient.objects.filter(
            student=student, school_year=active_year
        ).aggregate(total=models.Sum('amount'))['total'] or 0

        school_fee = SchoolFee.objects.filter(student=student, school_year=active_year).first()

        if not school_fee and student.school_class:
            school_fee = SchoolFee.objects.filter(
                school_class=student.school_class,
                student__isnull=True,
                school_year=active_year
            ).first()
        if not school_fee:
            school_fee = SchoolFee.objects.filter(
                school_class__isnull=True,
                student__isnull=True,
                school_year=active_year
            ).first()

        total_fee = sum([
            school_fee.school_fee or 0,
            school_fee.books_fee or 0,
            school_fee.trans_fee or 0,
            school_fee.clothes_fee or 0
        ]) if school_fee else 0

        return {
            'total_paid': total_paid,
            'total_fee': total_fee
        }

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
    driver_phone = serializers.SerializerMethodField()  # ✅ NEW: Add driver phone
    students = serializers.SerializerMethodField()  # ✅ Changed to method field to filter archived
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Bus
        fields = [
            'id', 'name', 'bus_number', 'bus_type',
            'capacity', 'phone_number', 'manager_name',
            'student_count', 'driver_name', 'driver_phone', 'students',
            'payments'
        ]

    def get_student_count(self, obj):
        # Only count non-archived students
        return obj.students.filter(is_archived=False).count()

    def get_driver_name(self, obj):
        if obj.driver:
            return f"{obj.driver.first_name} {obj.driver.last_name}".strip()
        return "غير محدد"

    def get_driver_phone(self, obj):
        """
        Return driver phone number if bus_type is 'داخلي' and driver exists
        """
        if obj.bus_type == "داخلي" and obj.driver:
            return obj.driver.phone_number or "غير محدد"
        return None  # Don't include phone for external buses or when no driver

    def get_students(self, obj):
        """
        Return only non-archived students
        """
        active_students = obj.students.filter(is_archived=False)
        return StudentBasicSerializer(active_students, many=True).data


class SchoolClassCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating school classes"""
    
    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'teacher']
        read_only_fields = ['id']

    def to_internal_value(self, data):
        """Debug what data is being received"""
        print(f"Received data in serializer: {data}")
        result = super().to_internal_value(data)
        print(f"After validation: {result}")
        return result

    def update(self, instance, validated_data):
        """Custom update method to ensure teacher is properly saved"""
        print(f"Updating class {instance.name} with validated data: {validated_data}")
        
        # Explicitly handle teacher field
        if 'teacher' in validated_data:
            teacher = validated_data['teacher']
            print(f"Setting teacher to: {teacher}")
            instance.teacher = teacher
        
        if 'name' in validated_data:
            instance.name = validated_data['name']
        
        instance.save()
        
        # Refresh from database to verify
        instance.refresh_from_db()
        print(f"After save and refresh - Class: {instance.name}, Teacher: {instance.teacher}")
        
        return instance


class SchoolClassListSerializer(serializers.ModelSerializer):
    """Serializer for listing school classes"""
    student_count = serializers.SerializerMethodField()
    teacher = serializers.SerializerMethodField()

    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'student_count', 'teacher']

    def get_student_count(self, obj):
        # Only count non-archived students
        return obj.students.filter(is_archived=False).count()

    def get_teacher(self, obj):
        if obj.teacher:
            return f"{obj.teacher.first_name} {obj.teacher.last_name}".strip()
        return "غير محدد"


class SchoolClassDetailSerializer(serializers.ModelSerializer):
    students = serializers.SerializerMethodField()  # ✅ Changed to method field to filter archived
    teacher = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    active_student_count = serializers.SerializerMethodField()
    archived_student_count = serializers.SerializerMethodField()

    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'students', 'teacher', 'teacher_name', 'active_student_count', 'archived_student_count']

    def get_students(self, obj):
        """
        Return only non-archived students
        """
        active_students = obj.students.filter(is_archived=False)
        return StudentSerializer(active_students, many=True).data

    def get_teacher(self, obj):
        """Return teacher name for backward compatibility"""
        if obj.teacher:
            return f"{obj.teacher.first_name} {obj.teacher.last_name}".strip()
        return "غير محدد"

    def get_teacher_name(self, obj):
        """Return teacher name (same as get_teacher but more explicit)"""
        if obj.teacher:
            return f"{obj.teacher.first_name} {obj.teacher.last_name}".strip()
        return "غير محدد"

    def get_active_student_count(self, obj):
        """Count only non-archived students"""
        return obj.students.filter(is_archived=False).count()

    def get_archived_student_count(self, obj):
        """Count only archived students"""
        return obj.students.filter(is_archived=True).count()


class BusCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = [
            'id', 'name', 'bus_number', 'bus_type',
            'capacity', 'phone_number', 'manager_name', 'driver'
        ]
        read_only_fields = ['id']


class SchoolClassRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SchoolClassDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        # Filter by user's account
        return SchoolClass.objects.filter(account=self.request.user.account)
    
    def get_serializer_context(self):
        # Add request context to serializer
        context = super().get_serializer_context()
        context['request'] = self.request
        return context