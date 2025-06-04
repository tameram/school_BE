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
        exclude = ['account', 'created_by']
    
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
    
class SimplePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'number', 'amount', 'date', 'reason']

class RecipientSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    parent_phone = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    cheque = ChequeDetailSerializer(read_only=True)

    class Meta:
        model = Recipient
        fields = '__all__'  # Includes all model fields + custom fields below
        # OR explicitly: ['id', 'amount', 'date', ..., 'student_name', 'student_id', 'parent_name', 'parent_phone', 'class_name', 'cheque']

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.first_name} {obj.student.second_name}".strip()
        return "غير معروف"

    def get_student_id(self, obj):
        return obj.student.student_id if obj.student else None

    def get_parent_name(self, obj):
        return obj.student.parent_name if obj.student else None

    def get_parent_phone(self, obj):
        return obj.student.parent_phone if obj.student else None

    def get_class_name(self, obj):
        if obj.student and obj.student.school_class:
            return obj.student.school_class.name
        return None
   