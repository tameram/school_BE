from rest_framework import serializers
from .models import PaymentType, BankTransferDetail, ChequeDetail,  Payment, Recipient

class PaymentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentType
        fields = ['id', 'name', 'display_name', 'type']


class BankTransferDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransferDetail
        fields = ['id', 'bank_number', 'branch_number', 'account_number']


class ChequeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChequeDetail
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    cheque_details = ChequeDetailSerializer(required=False, write_only=True)
    target_name = serializers.SerializerMethodField()
    class Meta:
        model = Payment
        fields = '__all__'  # or list each field if preferred
        extra_kwargs = {
            'id': {'read_only': True}
        }
    
    def get_target_name(self, obj):
        if obj.payment_type == 'متفرقات':
            return 'متفرقات'

        if obj.recipient_employee:
            return f"{obj.recipient_employee.first_name} {obj.recipient_employee.last_name}".strip()

        if obj.recipient_bus:
            return f"{obj.recipient_bus.name or ''} {obj.recipient_bus.bus_number or ''}".strip()

        if obj.recipient_authorized:
            return obj.recipient_authorized.display_value or obj.recipient_authorized.name

        return 'متفرقات'

    def create(self, validated_data):
        cheque_data = validated_data.pop('cheque_details', None)
        payment = Payment.objects.create(**validated_data)

        if cheque_data:
            cheque = ChequeDetail.objects.create(**cheque_data)
            payment.cheque = cheque  # ✅ assign to the actual ForeignKey field
            payment.save()

        return payment

class RecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = '__all__'