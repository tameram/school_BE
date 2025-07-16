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
    total_fees_before_discount = serializers.ReadOnlyField(source='get_total_fees_before_discount')
    discount_amount_calculated = serializers.ReadOnlyField(source='get_discount_amount_calculated')
    total_fees_after_discount = serializers.ReadOnlyField(source='get_total_fees_after_discount')
    
    class Meta:
        model = SchoolFee
        exclude = ['account', 'created_by']

    def to_representation(self, instance):
        """Ensure all fields are properly represented"""
        data = super().to_representation(instance)
        
        # Ensure boolean field is present
        if 'clothes_fee_paid' not in data:
            data['clothes_fee_paid'] = False
            
        # Ensure discount fields have default values
        if data.get('discount_percentage') is None:
            data['discount_percentage'] = 0
        if data.get('discount_amount') is None:
            data['discount_amount'] = 0
            
        return data

    def validate(self, data):
        """Validate discount fields"""
        discount_percentage = data.get('discount_percentage', 0)
        discount_amount = data.get('discount_amount', 0)
        
        # Validate percentage is between 0 and 100
        if discount_percentage and (discount_percentage < 0 or discount_percentage > 100):
            raise serializers.ValidationError({
                'discount_percentage': 'Discount percentage must be between 0 and 100'
            })
        
        # Validate discount amount is not negative
        if discount_amount and discount_amount < 0:
            raise serializers.ValidationError({
                'discount_amount': 'Discount amount cannot be negative'
            })
        
        return data

class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = ['id', 'label', 'is_active', 'start_date', 'end_date']