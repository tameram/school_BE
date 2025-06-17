from rest_framework import serializers
from datetime import date
from django.db.models import Sum, Q
from decimal import Decimal

from .models import Employee, EmployeeHistory, EmployeeVirtualTransaction
from payments.models import Payment
from payments.serializers import PaymentSerializer, SimplePaymentSerializer


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

    is_teacher = serializers.SerializerMethodField()
    is_driver = serializers.SerializerMethodField()
    total_paid_this_month = serializers.SerializerMethodField()
    outstanding_balance_current_month = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        exclude = ['account', 'created_by']

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
        Outstanding = (Base Salary + Virtual Credits - Virtual Debits) - Total Paid
        """
        today = date.today()
        
        # Get base salary (monthly)
        base_salary = obj.base_salary or Decimal('0')
        
        # Get virtual transactions for current month
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
        
        # Get payments for current month
        current_month_payments = Payment.objects.filter(
            recipient_employee=obj,
            account=obj.account,
            date__year=today.year,
            date__month=today.month
        ).aggregate(
            total_paid=Sum('amount')
        )
        
        total_paid = current_month_payments['total_paid'] or Decimal('0')
        
        # Calculate outstanding balance
        should_receive = base_salary + virtual_credits - virtual_debits
        outstanding_balance = should_receive - total_paid
        
        return float(outstanding_balance)

    def validate(self, attrs):
        """
        Custom validation to prevent archiving employees under certain conditions
        """
        # Only validate if we're trying to archive the employee
        if attrs.get('is_archived') and self.instance:
            employee = self.instance
            
            # 1. Check if employee is a teacher assigned to a class
            if employee.employee_type and employee.employee_type.is_teacher:
                # Import here to avoid circular imports
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
            
            # 2. Check if employee is a driver assigned to a bus
            if employee.employee_type and employee.employee_type.is_driver:
                # Import here to avoid circular imports
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
            
            # 3. Check if employee has outstanding money for current month
            today = date.today()
            
            # Get base salary (monthly)
            base_salary = employee.base_salary or Decimal('0')
            
            # Get virtual transactions for current month
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
            
            # Get payments for current month
            current_month_payments = Payment.objects.filter(
                recipient_employee=employee,
                account=employee.account,
                date__year=today.year,
                date__month=today.month
            ).aggregate(
                total_paid=Sum('amount')
            )
            
            total_paid = current_month_payments['total_paid'] or Decimal('0')
            
            # Calculate outstanding balance
            # What employee should receive = base_salary + virtual_credits - virtual_debits
            # What employee actually received = total_paid
            # Outstanding = Should receive - Actually received
            should_receive = base_salary + virtual_credits - virtual_debits
            outstanding_balance = should_receive - total_paid
            
            if outstanding_balance > 0:
                raise serializers.ValidationError({
                    'is_archived': f'لا يمكن أرشفة الموظف لأن له مبلغ مستحق قدره {outstanding_balance} شيكل لهذا الشهر'
                })
        
        return attrs