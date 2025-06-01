from rest_framework import serializers
from .models import Employee, EmployeeHistory
from payments.serializers import PaymentSerializer, SimplePaymentSerializer


class EmployeeHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeHistory
        fields = ['id', 'event', 'note', 'date']


class EmployeeSerializer(serializers.ModelSerializer):
    history = EmployeeHistorySerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    
    is_teacher = serializers.SerializerMethodField()
    is_driver = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        exclude = ['account', 'created_by']

    def get_is_teacher(self, obj):
        return obj.employee_type.is_teacher if obj.employee_type else False

    def get_is_driver(self, obj):
        return obj.employee_type.is_driver if obj.employee_type else False

