from rest_framework import serializers
from .models import EmployeeType, AuthorizedPayer, SchoolFee, SchoolYear

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
        # This will automatically include the new 'clothes_fee_paid' field

    def to_representation(self, instance):
        """Ensure clothes_fee_paid is always included in the response"""
        data = super().to_representation(instance)
        # Ensure the field is present even if it's None
        if 'clothes_fee_paid' not in data:
            data['clothes_fee_paid'] = False
        return data

class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = ['id', 'label', 'is_active', 'start_date', 'end_date']

