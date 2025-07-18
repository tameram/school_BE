from rest_framework import serializers
from utils.s3_utils import S3FileManager


from payments.serializers import PaymentSerializer, RecipientSerializer
from .models import Student, SchoolClass, StudentHistory, Bus, StudentDocument
from rest_framework import generics
from payments.models import Recipient
from settings_data.serializers import SchoolFeeSerializer
from settings_data.models import SchoolYear, SchoolFee
from django.db import models
from rest_framework.permissions import IsAuthenticated

import logging
logger = logging.getLogger(__name__)


class StudentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentHistory
        fields = ['id', 'event', 'note', 'date']

class StudentDocumentSerializer(serializers.ModelSerializer):
    document_url = serializers.SerializerMethodField()
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = StudentDocument
        fields = ['id', 'document_type', 'document_type_display', 'document', 'document_url', 
                 'description', 'uploaded_at']
    
    def get_document_url(self, obj):
        """Return the full URL for the document file"""
        if obj.document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document.url)
            return obj.document.url
        return None


class StudentSerializer(serializers.ModelSerializer):
    history = StudentHistorySerializer(many=True, read_only=True)
    recipients = RecipientSerializer(many=True, read_only=True, source='recipient_set')
    school_fees = serializers.SerializerMethodField()
    school_fees_by_year = serializers.SerializerMethodField()
    payment_summary = serializers.SerializerMethodField()
    documents = StudentDocumentSerializer(many=True, read_only=True)
    attachment_url = serializers.SerializerMethodField()
    
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

    def validate_is_archived(self, value):
        """
        Validate that student can only be archived if they don't have outstanding payments
        """
        # Only validate when trying to set is_archived to True
        if value is True and self.instance:
            student = self.instance
            
            # Get the active school year
            active_year = SchoolYear.objects.filter(
                account=student.account, 
                is_active=True
            ).first()
            
            if active_year:
                # Calculate total paid for current year
                total_paid = Recipient.objects.filter(
                    student=student, 
                    school_year=active_year
                ).aggregate(total=models.Sum('amount'))['total'] or 0

                # Find applicable school fee with fallback logic
                school_fee = SchoolFee.objects.filter(
                    student=student, 
                    school_year=active_year
                ).first()

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

                # Calculate total required fee
                if school_fee:
                    if fee:
                        total_fee = fee.get_total_fees_after_discount()  # Uses discount-aware calculation
                    else:
                        total_fee = 0
                    
                    # Check if there are outstanding payments
                    outstanding_amount = total_fee - total_paid
                    
                    if outstanding_amount > 0:
                        raise serializers.ValidationError(
                            f"لا يمكن أرشفة الطالب لوجود مستحقات غير مدفوعة بقيمة {outstanding_amount:.2f}. "
                            f"يجب تسوية المستحقات أو إغلاق الحساب أولاً."
                        )
        
        return value

    def validate(self, data):
        """
        Additional cross-field validation for archiving
        """
        # Check if student is being archived and has bus assignment
        if (data.get('is_archived') is True and 
            self.instance and 
            (self.instance.is_bus_joined or self.instance.bus)):
            
            # Optionally, you might want to warn about bus assignment
            # or automatically remove bus assignment when archiving
            pass
        
        return data

    def get_attachment_url(self, obj):
        """
        Generate URL for attachment with correct path handling
        """
        if not obj.attachment:
            return None
        
        try:
            # Method 1: Use Django's built-in URL generation (recommended)
            url = obj.attachment.url
            logger.info(f"Django generated URL for student {obj.id}: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error getting Django URL for student {obj.id}: {e}")
            
            # Method 2: Manual construction as fallback
            try:
                # obj.attachment.name already includes the full path from your upload_to function
                # It should be something like: "test1/students/student/uuid/filename.png"
                file_path = obj.attachment.name
                
                # Check if the path already includes 'media/' prefix
                if not file_path.startswith('media/'):
                    file_path = f"media/{file_path}"
                
                # Construct the full S3 URL
                base_url = "https://daftar-noon.s3.il-central-1.amazonaws.com/"
                manual_url = f"{base_url}{file_path}"
                
                logger.info(f"Manual URL for student {obj.id}: {manual_url}")
                return manual_url
                
            except Exception as manual_error:
                logger.error(f"Manual URL generation failed for student {obj.id}: {manual_error}")
                return None


    def get_school_fees_by_year(self, student):
        fees = SchoolFee.objects.filter(student=student)
        return [
            {
                "school_fee": f.school_fee,
                "books_fee": f.books_fee,
                "trans_fee": f.trans_fee,
                "clothes_fee": f.clothes_fee,
                "clothes_fee_paid": f.clothes_fee_paid,
                "school_year": str(f.school_year.id) if f.school_year else None
            } for f in fees
        ]
    
    def get_payment_summary(self, student):
        active_year = SchoolYear.objects.filter(account=student.account, is_active=True).first()
        if not active_year:
            return {'total_paid': 0, 'total_fee': 0, 'total_discount': 0, 'final_fee': 0}

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

        if school_fee:
            # USE THE NEW DISCOUNT-AWARE METHODS
            total_fee_before_discount = school_fee.get_total_fees_before_discount()
            total_discount = school_fee.get_discount_amount_calculated()
            final_fee = school_fee.get_total_fees_after_discount()
        else:
            total_fee_before_discount = 0
            total_discount = 0
            final_fee = 0

        return {
            'total_paid': total_paid,
            'total_fee_before_discount': total_fee_before_discount,  # NEW
            'total_discount': total_discount,                        # NEW
            'final_fee': final_fee,                                  # NEW
            'remaining_amount': max(final_fee - total_paid, 0),      # UPDATED
            # Keep backward compatibility
            'total_fee': final_fee  # This maintains existing frontend compatibility
        }

    def get_school_fees(self, student):
        fee = SchoolFee.objects.filter(student=student).first()
        if fee:
            return {
                'school_fee': fee.school_fee,
                'books_fee': fee.books_fee,
                'trans_fee': fee.trans_fee,
                'clothes_fee': fee.clothes_fee,
                'clothes_fee_paid': fee.clothes_fee_paid,
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
                    'clothes_fee_paid': fee.clothes_fee_paid,
                    'id': fee.id
                }

        fee = SchoolFee.objects.filter(student__isnull=True, school_class__isnull=True, account=student.account).first()
        if fee:
            return {
                'school_fee': fee.school_fee,
                'books_fee': fee.books_fee,
                'trans_fee': fee.trans_fee,
                'clothes_fee': fee.clothes_fee,
                'clothes_fee_paid': fee.clothes_fee_paid,
                'id': fee.id
            }

        return None

class StudentBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'first_name', 'second_name', 'student_id', 'school_class', 'address']


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
    """Serializer for creating and updating school classes - Simplified Version"""
    
    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'teacher']
        read_only_fields = ['id']

    def validate_name(self, value):
        """Validate that class name is unique within the account"""
        if not value:
            raise serializers.ValidationError("اسم الصف مطلوب")
        
        # Clean the value
        cleaned_value = value.strip()
        if not cleaned_value:
            raise serializers.ValidationError("اسم الصف لا يمكن أن يكون فارغاً")
        
        # Get the account from the request context
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'account'):
            raise serializers.ValidationError("لا يمكن التحقق من صحة البيانات")
        
        account = request.user.account
        
        # Check for existing class with same name in the same account (case-insensitive)
        existing_class = SchoolClass.objects.filter(
            name__iexact=cleaned_value, 
            account=account
        )
        
        # If updating, exclude the current instance
        if self.instance:
            existing_class = existing_class.exclude(id=self.instance.id)
        
        if existing_class.exists():
            raise serializers.ValidationError("يوجد صف بنفس الاسم ")
        
        return cleaned_value

    def validate_teacher(self, value):
        """Validate that teacher exists and is active - Simplified"""
        if not value:
            raise serializers.ValidationError("المعلم المسؤول مطلوب")
        
        # Get the account from the request context
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'account'):
            raise serializers.ValidationError("لا يمكن التحقق من صحة البيانات")
        
        account = request.user.account
        
        # Import here to avoid circular imports
        from employees.models import Employee
        
        # Check if employee exists, is active, and belongs to the same account
        try:
            teacher = Employee.objects.get(
                id=value.id if hasattr(value, 'id') else value,
                account=account,
                is_archived=False
            )
            return teacher
            
        except Employee.DoesNotExist:
            raise serializers.ValidationError("الموظف المحدد غير موجود أو غير مفعل")

    def to_internal_value(self, data):
        """Debug what data is being received"""
        print(f"📥 Received data in serializer: {data}")
        result = super().to_internal_value(data)
        print(f"✅ After validation: {result}")
        return result

    def update(self, instance, validated_data):
        """Custom update method with proper logging"""
        print(f"🔄 Updating class {instance.name} with validated data: {validated_data}")
        
        # Update all fields from validated_data
        for field, value in validated_data.items():
            setattr(instance, field, value)
            print(f"Set {field} = {value}")
        
        instance.save()
        
        # Refresh from database to verify
        instance.refresh_from_db()
        print(f"✅ After save and refresh - Class: {instance.name}, Teacher: {instance.teacher}")
        
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

    def validate_name(self, value):
        """Validate that bus name is unique within the account"""
        if not value:
            raise serializers.ValidationError("اسم الحافلة مطلوب")
        
        # Clean the value
        cleaned_value = value.strip()
        if not cleaned_value:
            raise serializers.ValidationError("اسم الحافلة لا يمكن أن يكون فارغاً")
        
        # Get the account from the request context
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'account'):
            raise serializers.ValidationError("لا يمكن التحقق من صحة البيانات")
        
        account = request.user.account
        
        # Check for existing bus with same name in the same account (case-insensitive)
        existing_bus = Bus.objects.filter(
            name__iexact=cleaned_value, 
            account=account
        )
        
        # If updating, exclude the current instance
        if self.instance:
            existing_bus = existing_bus.exclude(id=self.instance.id)
        
        if existing_bus.exists():
            raise serializers.ValidationError("يوجد حافلة بنفس الاسم ")
        
        return cleaned_value

    def validate_bus_number(self, value):
        """Validate that bus number is unique within the account"""
        if not value:
            raise serializers.ValidationError("رقم اللوحة مطلوب")
        
        # Clean the value
        cleaned_value = value.strip()
        if not cleaned_value:
            raise serializers.ValidationError("رقم اللوحة لا يمكن أن يكون فارغاً")
        
        # Get the account from the request context
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'account'):
            raise serializers.ValidationError("لا يمكن التحقق من صحة البيانات")
        
        account = request.user.account
        
        # Check for existing bus with same number in the same account (case-insensitive)
        existing_bus = Bus.objects.filter(
            bus_number__iexact=cleaned_value, 
            account=account
        )
        
        # If updating, exclude the current instance
        if self.instance:
            existing_bus = existing_bus.exclude(id=self.instance.id)
        
        if existing_bus.exists():
            raise serializers.ValidationError("يوجد حافلة بنفس رقم اللوحة ")
        
        return cleaned_value

    def validate_bus_type(self, value):
        """Validate bus type"""
        if not value:
            raise serializers.ValidationError("نوع الحافلة مطلوب")
        
        allowed_types = ['داخلي', 'خارجي']
        if value not in allowed_types:
            raise serializers.ValidationError(f"نوع الحافلة يجب أن يكون أحد القيم التالية: {', '.join(allowed_types)}")
        
        return value

    def validate_capacity(self, value):
        """Validate bus capacity"""
        if not value:
            raise serializers.ValidationError("سعة الحافلة مطلوبة")
        
        if value < 1:
            raise serializers.ValidationError("سعة الحافلة يجب أن تكون أكبر من صفر")
        
        if value > 100:  # Reasonable upper limit
            raise serializers.ValidationError("سعة الحافلة كبيرة جداً")
        
        return value

    def validate_driver(self, value):
        """Validate driver for internal buses"""
        # This validation will be called if driver field is provided
        if value:
            # Get the account from the request context
            request = self.context.get('request')
            if not request or not hasattr(request.user, 'account'):
                raise serializers.ValidationError("لا يمكن التحقق من صحة البيانات")
            
            account = request.user.account
            
            # Import here to avoid circular imports
            from employees.models import Employee
            
            # Check if driver exists, is active, and belongs to the same account
            try:
                driver = Employee.objects.get(
                    id=value.id if hasattr(value, 'id') else value,
                    account=account,
                    is_archived=False
                )
                return driver
                
            except Employee.DoesNotExist:
                raise serializers.ValidationError("السائق المحدد غير موجود أو غير مفعل")
        
        return value

    def validate_phone_number(self, value):
        """Validate phone number for external buses"""
        if value:
            cleaned_value = value.strip()
            if len(cleaned_value) < 10:
                raise serializers.ValidationError("رقم الهاتف قصير جداً")
            if len(cleaned_value) > 15:
                raise serializers.ValidationError("رقم الهاتف طويل جداً")
            return cleaned_value
        return value

    def validate_manager_name(self, value):
        """Validate manager name for external buses"""
        if value:
            cleaned_value = value.strip()
            if not cleaned_value:
                raise serializers.ValidationError("اسم المسؤول لا يمكن أن يكون فارغاً")
            return cleaned_value
        return value

    def validate(self, data):
        """Cross-field validation"""
        bus_type = data.get('bus_type')
        driver = data.get('driver')
        manager_name = data.get('manager_name')
        phone_number = data.get('phone_number')
        
        if bus_type == 'داخلي':
            if not driver:
                raise serializers.ValidationError({
                    'driver': 'السائق مطلوب للحافلات الداخلية'
                })
            # Clear external bus fields for internal buses
            data['manager_name'] = None
            data['phone_number'] = None
            
        elif bus_type == 'خارجي':
            if not manager_name:
                raise serializers.ValidationError({
                    'manager_name': 'اسم المسؤول مطلوب للحافلات الخارجية'
                })
            if not phone_number:
                raise serializers.ValidationError({
                    'phone_number': 'رقم الهاتف مطلوب للحافلات الخارجية'
                })
            # Clear driver field for external buses
            data['driver'] = None
        
        return data

    def to_internal_value(self, data):
        """Debug what data is being received"""
        print(f"📥 Received bus data in serializer: {data}")
        result = super().to_internal_value(data)
        print(f"✅ After bus validation: {result}")
        return result

    def create(self, validated_data):
        """Custom create method with logging"""
        print(f"🔨 Creating bus with validated data: {validated_data}")
        instance = super().create(validated_data)
        print(f"✅ Created bus: {instance.name} ({instance.bus_number})")
        return instance

    def update(self, instance, validated_data):
        """Custom update method with logging"""
        print(f"🔄 Updating bus {instance.name} with validated data: {validated_data}")
        
        # Update all fields from validated_data
        for field, value in validated_data.items():
            setattr(instance, field, value)
            print(f"Set {field} = {value}")
        
        instance.save()
        
        # Refresh from database to verify
        instance.refresh_from_db()
        print(f"✅ After save and refresh - Bus: {instance.name} ({instance.bus_number})")
        
        return instance

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