from rest_framework import serializers
from datetime import date
from django.db.models import Sum, Q
from decimal import Decimal
import logging

from .models import Employee, EmployeeHistory, EmployeeVirtualTransaction, EmployeeDocument
from payments.models import Payment
from payments.serializers import PaymentSerializer, SimplePaymentSerializer

logger = logging.getLogger(__name__)


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    document_url = serializers.SerializerMethodField()
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = EmployeeDocument
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


class EmployeeHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeHistory
        fields = ['id', 'event', 'note', 'date']


class EmployeeVirtualTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeVirtualTransaction
        fields = '__all__'
        read_only_fields = ['account', 'created_by']


class EmployeeSerializer(serializers.ModelSerializer):
    history = EmployeeHistorySerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    virtual_transactions = EmployeeVirtualTransactionSerializer(many=True, read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)

    is_teacher = serializers.SerializerMethodField()
    is_driver = serializers.SerializerMethodField()
    total_paid_this_month = serializers.SerializerMethodField()
    outstanding_balance_current_month = serializers.SerializerMethodField()
    
    # File URL fields
    contract_pdf_url = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    id_copy_url = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        exclude = ['account', 'created_by']

    def get_contract_pdf_url(self, obj):
        """Generate URL for contract PDF"""
        return self._get_file_url(obj.contract_pdf)
    
    def get_profile_picture_url(self, obj):
        """Generate URL for profile picture"""
        return self._get_file_url(obj.profile_picture)
    
    def get_id_copy_url(self, obj):
        """Generate URL for ID copy"""
        return self._get_file_url(obj.id_copy)
    
    def _get_file_url(self, file_field):
        """Helper method to generate file URLs with error handling"""
        if not file_field:
            return None
        
        try:
            # Method 1: Use Django's built-in URL generation
            url = file_field.url
            logger.info(f"Django generated URL: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error getting Django URL: {e}")
            
            # Method 2: Manual construction as fallback
            try:
                file_path = file_field.name
                
                if not file_path.startswith('media/'):
                    file_path = f"media/{file_path}"
                
                base_url = "https://daftar-noon.s3.il-central-1.amazonaws.com/"
                manual_url = f"{base_url}{file_path}"
                
                logger.info(f"Manual URL: {manual_url}")
                return manual_url
                
            except Exception as manual_error:
                logger.error(f"Manual URL generation failed: {manual_error}")
                return None

    def validate_employee_id(self, value):
        """
        Validate that employee_id is unique within the account.
        """
        if not value:
            return value

        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("لا يمكن التحقق من معرف الموظف")

        account = request.user.account

        existing_query = Employee.objects.filter(
            employee_id=value,
            account=account
        )

        if self.instance:
            existing_query = existing_query.exclude(id=self.instance.id)

        if existing_query.exists():
            existing_employee = existing_query.first()
            raise serializers.ValidationError(
                f"معرف الموظف '{value}' موجود بالفعل للموظف {existing_employee.first_name} {existing_employee.last_name}"
            )

        return value

    def get_is_teacher(self, obj):
        return obj.employee_type.is_teacher if obj.employee_type else False

    def get_is_driver(self, obj):
        return obj.employee_type.is_driver if obj.employee_type else False
    
    def get_total_paid_this_month(self, obj):
        today = date.today()
        return Payment.objects.filter(
            recipient_employee=obj,
            date__year=today.year,
            date__month=today.month,
            account=obj.account
        ).aggregate(total=Sum('amount'))['total'] or 0

    def get_outstanding_balance_current_month(self, obj):
        """
        Calculate the outstanding balance for the current month
        """
        today = date.today()
        
        base_salary = obj.base_salary or Decimal('0')
        
        current_month_virtual = EmployeeVirtualTransaction.objects.filter(
            employee=obj,
            account=obj.account,
            date__year=today.year,
            date__month=today.month
        ).aggregate(
            credit_total=Sum('amount', filter=Q(direction='credit')),
            debit_total=Sum('amount', filter=Q(direction='debit'))
        )
        
        virtual_credits = current_month_virtual['credit_total'] or Decimal('0')
        virtual_debits = current_month_virtual['debit_total'] or Decimal('0')
        
        current_month_payments = Payment.objects.filter(
            recipient_employee=obj,
            account=obj.account,
            date__year=today.year,
            date__month=today.month
        ).aggregate(
            total_paid=Sum('amount')
        )
        
        total_paid = current_month_payments['total_paid'] or Decimal('0')
        
        should_receive = base_salary + virtual_credits - virtual_debits
        outstanding_balance = should_receive - total_paid
        
        return float(outstanding_balance)

    def validate(self, attrs):
        """
        Custom validation to prevent archiving employees under certain conditions
        """
        if attrs.get('is_archived') and self.instance:
            employee = self.instance
            
            # Check if employee is a teacher assigned to a class
            if employee.employee_type and employee.employee_type.is_teacher:
                from students.models import SchoolClass
                
                assigned_classes = SchoolClass.objects.filter(
                    teacher=employee,
                    account=employee.account
                )
                
                if assigned_classes.exists():
                    class_names = list(assigned_classes.values_list('name', flat=True))
                    raise serializers.ValidationError({
                        'is_archived': f'لا يمكن أرشفة المعلم لأنه مسؤول عن الفصول التالية: {", ".join(class_names)}'
                    })
            
            # Check if employee is a driver assigned to a bus
            if employee.employee_type and employee.employee_type.is_driver:
                from students.models import Bus
                
                assigned_buses = Bus.objects.filter(
                    driver=employee,
                    account=employee.account
                )
                
                if assigned_buses.exists():
                    bus_names = list(assigned_buses.values_list('name', flat=True))
                    raise serializers.ValidationError({
                        'is_archived': f'لا يمكن أرشفة السائق لأنه مسؤول عن الحافلات التالية: {", ".join(bus_names)}'
                    })
            
            # Check outstanding balance
            today = date.today()
            base_salary = employee.base_salary or Decimal('0')
            
            current_month_virtual = EmployeeVirtualTransaction.objects.filter(
                employee=employee,
                account=employee.account,
                date__year=today.year,
                date__month=today.month
            ).aggregate(
                credit_total=Sum('amount', filter=Q(direction='credit')),
                debit_total=Sum('amount', filter=Q(direction='debit'))
            )
            
            virtual_credits = current_month_virtual['credit_total'] or Decimal('0')
            virtual_debits = current_month_virtual['debit_total'] or Decimal('0')
            
            current_month_payments = Payment.objects.filter(
                recipient_employee=employee,
                account=employee.account,
                date__year=today.year,
                date__month=today.month
            ).aggregate(
                total_paid=Sum('amount')
            )
            
            total_paid = current_month_payments['total_paid'] or Decimal('0')
            
            should_receive = base_salary + virtual_credits - virtual_debits
            outstanding_balance = should_receive - total_paid
            
            if outstanding_balance > 0:
                raise serializers.ValidationError({
                    'is_archived': f'لا يمكن أرشفة الموظف لأن له مبلغ مستحق قدره {outstanding_balance} شيكل لهذا الشهر'
                })
        
        return attrs

