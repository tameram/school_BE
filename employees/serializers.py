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

    class Meta:
        model = Employee
        fields = '__all__'

