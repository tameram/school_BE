from rest_framework import serializers
from .models import EmployeeType, AuthorizedPayer, SchoolFee

class EmployeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeType
        fields = '__all__'

class AuthorizedPayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorizedPayer
        fields = '__all__'

class SchoolFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolFee
        exclude = ['account', 'created_by']
