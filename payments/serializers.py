from rest_framework import serializers
from django.utils import timezone
import logging
from .models import PaymentType, BankTransferDetail, ChequeDetail, Payment, Recipient, PaymentDocument

logger = logging.getLogger(__name__)


class PaymentDocumentSerializer(serializers.ModelSerializer):
    document_url = serializers.SerializerMethodField()
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = PaymentDocument
        fields = ['id', 'document_type', 'document_type_display', 'document', 'document_url', 
                 'description', 'uploaded_at']
    
    def get_document_url(self, obj):
        """Return the full URL for the document file"""
        if obj.document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document.url)
            return obj.document.url
        return None


class PaymentTypeSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentType
        fields = ['id', 'name', 'display_name', 'type', 'created_by', 'created_by_name']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name or ''} {obj.created_by.last_name or ''}".strip()
        return None


class BankTransferDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransferDetail
        fields = ['id', 'bank_number', 'branch_number', 'account_number']


class ChequeDetailSerializer(serializers.ModelSerializer):
    cheque_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ChequeDetail
        fields = ['id', 'bank_number', 'branch_number', 'account_number', 
                 'cheque_number', 'cheque_date', 'cheque_image', 'cheque_image_url', 
                 'description']
    
    def get_cheque_image_url(self, obj):
        """Generate URL for cheque image with error handling"""
        if not obj.cheque_image:
            return None
        
        try:
            # Method 1: Use Django's built-in URL generation
            url = obj.cheque_image.url
            logger.info(f"Django generated URL for cheque {obj.id}: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error getting Django URL for cheque {obj.id}: {e}")
            
            # Method 2: Manual construction as fallback
            try:
                file_path = obj.cheque_image.name
                
                if not file_path.startswith('media/'):
                    file_path = f"media/{file_path}"
                
                base_url = "https://daftar-noon.s3.il-central-1.amazonaws.com/"
                manual_url = f"{base_url}{file_path}"
                
                logger.info(f"Manual URL for cheque {obj.id}: {manual_url}")
                return manual_url
                
            except Exception as manual_error:
                logger.error(f"Manual URL generation failed for cheque {obj.id}: {manual_error}")
                return None


class PaymentSerializer(serializers.ModelSerializer):
    # For write operations (create/update) - nested cheque data
    cheque_details = ChequeDetailSerializer(required=False, write_only=True)
    
    # For read operations - include the actual cheque details
    cheque = ChequeDetailSerializer(read_only=True)
    
    target_name = serializers.SerializerMethodField()
    documents = PaymentDocumentSerializer(many=True, read_only=True)
    
    # Format time display
    time_display = serializers.SerializerMethodField()
    datetime_display = serializers.SerializerMethodField()
    
    # Add created_by and school_year details
    created_by_name = serializers.SerializerMethodField()
    school_year_label = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        exclude = ['account']
    
    def get_created_by_name(self, obj):
        """Return created_by first_name + last_name"""
        if obj.created_by:
            return f"{obj.created_by.first_name or ''} {obj.created_by.last_name or ''}".strip()
        return None
    
    def get_school_year_label(self, obj):
        """Return school_year label"""
        if obj.school_year:
            return obj.school_year.label
        return None
    
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
            data['cheque'] = ChequeDetailSerializer(instance.cheque, context=self.context).data
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
    created_by_name = serializers.SerializerMethodField()
    school_year_label = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = ['id', 'number', 'amount', 'date', 'time', 'time_display', 'reason', 
                 'created_by', 'created_by_name', 'school_year', 'school_year_label']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name or ''} {obj.created_by.last_name or ''}".strip()
        return None
    
    def get_school_year_label(self, obj):
        if obj.school_year:
            return obj.school_year.label
        return None
    
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
    
    # CRITICAL FIX: Explicit cheque serialization with context
    cheque = ChequeDetailSerializer(read_only=True)
    documents = PaymentDocumentSerializer(many=True, read_only=True)
    
    # For write operations - nested cheque data
    cheque_details = ChequeDetailSerializer(required=False, write_only=True)
    
    # Format time display
    time_display = serializers.SerializerMethodField()
    datetime_display = serializers.SerializerMethodField()
    
    # Add created_by and school_year details
    created_by_name = serializers.SerializerMethodField()
    school_year_label = serializers.SerializerMethodField()

    class Meta:
        model = Recipient
        fields = '__all__'
    
    def get_created_by_name(self, obj):
        """Return created_by first_name + last_name"""
        if obj.created_by:
            return f"{obj.created_by.first_name or ''} {obj.created_by.last_name or ''}".strip()
        return None
    
    def get_school_year_label(self, obj):
        """Return school_year label"""
        if obj.school_year:
            return obj.school_year.label
        return None
    
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
        CRITICAL FIX: Override to ensure cheque details are properly serialized with context
        """
        data = super().to_representation(instance)
        
        # Force load cheque relationship if it exists
        if hasattr(instance, 'cheque') and instance.cheque:
            try:
                # Ensure cheque is properly loaded from database
                cheque_instance = instance.cheque
                if cheque_instance:
                    # Pass context to include request for URL generation
                    data['cheque'] = ChequeDetailSerializer(cheque_instance, context=self.context).data
                    logger.info(f"✅ Serialized cheque data for recipient {instance.id}: {data['cheque']}")
                else:
                    data['cheque'] = None
                    logger.info(f"❌ No cheque found for recipient {instance.id}")
            except Exception as e:
                logger.error(f"❌ Error serializing cheque for recipient {instance.id}: {e}")
                data['cheque'] = None
        else:
            data['cheque'] = None
            logger.info(f"ℹ️ No cheque relationship for recipient {instance.id}")
            
        return data

    def create(self, validated_data):
        cheque_data = validated_data.pop('cheque_details', None)
        
        # Auto-populate date and time if not provided
        if 'date' not in validated_data or not validated_data['date']:
            validated_data['date'] = timezone.now().date()
        
        if 'time' not in validated_data or not validated_data['time']:
            validated_data['time'] = timezone.now().time()
        
        # Create recipient first
        recipient = Recipient.objects.create(**validated_data)
        
        # Handle cheque creation separately
        if cheque_data:
            cheque = ChequeDetail.objects.create(**cheque_data)
            recipient.cheque = cheque
            recipient.save()
            logger.info(f"✅ Created recipient {recipient.id} with cheque {cheque.id}")
        
        return recipient

    def update(self, instance, validated_data):
        cheque_data = validated_data.pop('cheque_details', None)
        
        # Update recipient fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Handle cheque data updates
        if cheque_data:
            if instance.cheque:
                # Update existing cheque
                for attr, value in cheque_data.items():
                    setattr(instance.cheque, attr, value)
                instance.cheque.save()
                logger.info(f"✅ Updated existing cheque {instance.cheque.id} for recipient {instance.id}")
            else:
                # Create new cheque
                cheque = ChequeDetail.objects.create(**cheque_data)
                instance.cheque = cheque
                logger.info(f"✅ Created new cheque {cheque.id} for recipient {instance.id}")
        
        instance.save()
        return instance

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

