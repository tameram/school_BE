from rest_framework import serializers
from datetime import date
from django.db.models import Sum

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



