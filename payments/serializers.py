from rest_framework import serializers
from django.utils import timezone
from .models import PaymentType, BankTransferDetail, ChequeDetail, Payment, Recipient


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
    # For write operations (create/update) - nested cheque data
    cheque_details = ChequeDetailSerializer(required=False, write_only=True)
    
    # For read operations - include the actual cheque details
    cheque = ChequeDetailSerializer(read_only=True)
    
    target_name = serializers.SerializerMethodField()
    
    # Format time display
    time_display = serializers.SerializerMethodField()
    datetime_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        exclude = ['account', 'created_by']
    
    def get_time_display(self, obj):
        """Return formatted time string"""
        if obj.time:
            return obj.time.strftime('%H:%M:%S')
        return None
    
    def get_datetime_display(self, obj):
        """Return formatted datetime string"""
        if obj.date and obj.time:
            return f"{obj.date} {obj.time.strftime('%H:%M:%S')}"
        return None
    
    def to_representation(self, instance):
        """
        Override to ensure cheque details are properly serialized
        """
        data = super().to_representation(instance)
        
        # Ensure cheque is properly serialized as an object, not just UUID
        if instance.cheque:
            data['cheque'] = ChequeDetailSerializer(instance.cheque).data
        else:
            data['cheque'] = None
            
        return data
    
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
        
        # Auto-populate date and time if not provided
        if 'date' not in validated_data or not validated_data['date']:
            validated_data['date'] = timezone.now().date()
        
        if 'time' not in validated_data or not validated_data['time']:
            validated_data['time'] = timezone.now().time()
        
        payment = Payment.objects.create(**validated_data)

        if cheque_data:
            cheque = ChequeDetail.objects.create(**cheque_data)
            payment.cheque = cheque
            payment.save()

        return payment

    def update(self, instance, validated_data):
        cheque_data = validated_data.pop('cheque_details', None)
        
        # Update payment fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Handle cheque data
        if cheque_data:
            if instance.cheque:
                # Update existing cheque
                for attr, value in cheque_data.items():
                    setattr(instance.cheque, attr, value)
                instance.cheque.save()
            else:
                # Create new cheque
                cheque = ChequeDetail.objects.create(**cheque_data)
                instance.cheque = cheque
        
        instance.save()
        return instance


class SimplePaymentSerializer(serializers.ModelSerializer):
    time_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = ['id', 'number', 'amount', 'date', 'time', 'time_display', 'reason']
    
    def get_time_display(self, obj):
        if obj.time:
            return obj.time.strftime('%H:%M:%S')
        return None


class RecipientSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    parent_phone = serializers.SerializerMethodField()
    class_name = serializers.SerializerMethodField()
    cheque = ChequeDetailSerializer(read_only=True)
    
    # Format time display
    time_display = serializers.SerializerMethodField()
    datetime_display = serializers.SerializerMethodField()

    class Meta:
        model = Recipient
        fields = '__all__'
    
    def get_time_display(self, obj):
        """Return formatted time string"""
        if obj.time:
            return obj.time.strftime('%H:%M:%S')
        return None
    
    def get_datetime_display(self, obj):
        """Return formatted datetime string"""
        if obj.date and obj.time:
            return f"{obj.date} {obj.time.strftime('%H:%M:%S')}"
        return None

    def to_representation(self, instance):
        """
        Override to ensure cheque details are properly serialized
        """
        data = super().to_representation(instance)
        
        # Ensure cheque is properly serialized as an object, not just UUID
        if instance.cheque:
            data['cheque'] = ChequeDetailSerializer(instance.cheque).data
        else:
            data['cheque'] = None
            
        return data

    def create(self, validated_data):
        # Auto-populate date and time if not provided
        if 'date' not in validated_data or not validated_data['date']:
            validated_data['date'] = timezone.now().date()
        
        if 'time' not in validated_data or not validated_data['time']:
            validated_data['time'] = timezone.now().time()
        
        return super().create(validated_data)

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