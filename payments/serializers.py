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
        fields = ['id', 'bank_number', 'branch_number', 'account_number', 'cheque_date', 'cheque_image']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class RecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = '__all__'