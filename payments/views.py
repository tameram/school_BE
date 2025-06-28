from rest_framework import viewsets, status, parsers
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from settings_data.models import SchoolYear
from .models import PaymentType, BankTransferDetail, ChequeDetail, Payment, Recipient, PaymentDocument
from .serializers import (
    PaymentTypeSerializer,
    BankTransferDetailSerializer,
    ChequeDetailSerializer,
    PaymentSerializer,
    RecipientSerializer,
    PaymentDocumentSerializer
)
from logs.utils import log_activity
from utils.s3_utils import S3FileManager
import logging

logger = logging.getLogger(__name__)


class PaymentTypeViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentTypeSerializer

    def get_queryset(self):
        return PaymentType.objects.filter(
            account=self.request.user.account
        ).select_related('created_by')

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(self.request.user, self.request.user.account, f"تم إنشاء نوع دفعة {instance.name}", 'PaymentType', str(instance.id))

    def perform_destroy(self, instance):
        log_activity(self.request.user, self.request.user.account, f"تم حذف نوع دفعة {instance.name}", 'PaymentType', str(instance.id))
        instance.delete()


class BankTransferDetailViewSet(viewsets.ModelViewSet):
    queryset = BankTransferDetail.objects.all()
    serializer_class = BankTransferDetailSerializer


class ChequeDetailViewSet(viewsets.ModelViewSet):
    queryset = ChequeDetail.objects.all()
    serializer_class = ChequeDetailSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_serializer_context(self):
        """Add request context to serializer for URL generation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class NotReceivedRecipientList(ListAPIView):
    serializer_class = RecipientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Recipient.objects.filter(
            account=user.account, 
            received=False
        ).select_related(
            'cheque', 
            'student', 
            'school_fee',
            'created_by',
            'school_year'
        )

    def get_serializer_context(self):
        """Add request context to serializer for URL generation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        account = self.request.user.account
        queryset = Payment.objects.filter(account=account).select_related(
            'cheque',
            'recipient_employee', 
            'recipient_bus', 
            'recipient_authorized',
            'authorized_payer',
            'school_year',
            'created_by'
        ).prefetch_related('documents')

        school_year_param = self.request.query_params.get('school_year')
        if school_year_param == 'current':
            active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
            if active_year:
                queryset = queryset.filter(school_year=active_year)
        return queryset

    def get_serializer_context(self):
        """Add request context to serializer for URL generation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve to ensure proper cheque data is included
        """
        instance = self.get_object()
        # Ensure the cheque is properly loaded
        if instance.cheque:
            # Force load the cheque to ensure it's in memory
            _ = instance.cheque.id
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def handle_cheque_data(self, request):
        """Handle cheque data from multipart form data with improved file handling"""
        logger.info("🔍 Debug: Incoming request data for cheque:", dict(request.data))
        logger.info("🔍 Debug: Incoming files:", dict(request.FILES))
        
        # Handle both nested and flat field formats
        cheque_data = {}
        
        # Try nested format first (cheque_details.field_name)
        nested_fields = {
            'bank_number': request.data.get('cheque_details.bank_number'),
            'branch_number': request.data.get('cheque_details.branch_number'), 
            'account_number': request.data.get('cheque_details.account_number'),
            'cheque_date': request.data.get('cheque_details.cheque_date'),
            'cheque_number': request.data.get('cheque_details.cheque_number'),
            'description': request.data.get('cheque_details.description')
        }
        
        # Try flat format as fallback
        flat_fields = {
            'bank_number': request.data.get('bankNumber'),
            'branch_number': request.data.get('branchNumber'),
            'account_number': request.data.get('accountNumber'), 
            'cheque_date': request.data.get('chequeDueDate'),
            'cheque_number': request.data.get('chequeNumber'),
            'description': request.data.get('description') or request.data.get('note')
        }
        
        # Use nested if available, otherwise fall back to flat
        for field in ['bank_number', 'branch_number', 'account_number', 'cheque_date', 'cheque_number', 'description']:
            if nested_fields[field]:
                cheque_data[field] = nested_fields[field]
            elif flat_fields[field]:
                cheque_data[field] = flat_fields[field]
        
        logger.info("🔍 Debug: Processed cheque data:", cheque_data)
        
        # Only create cheque if at least one field has data
        if any(value for value in cheque_data.values() if value):
            cheque = ChequeDetail.objects.create(**cheque_data)
            
            # Handle image upload with multiple possible field names
            image_file = (
                request.FILES.get('cheque_details.cheque_image') or 
                request.FILES.get('chequeImage') or
                request.FILES.get('cheque_image')
            )
            
            if image_file:
                try:
                    cheque.cheque_image = image_file
                    cheque.save()
                    logger.info(f"✅ Successfully uploaded cheque image for cheque {cheque.id}")
                except Exception as e:
                    logger.error(f"❌ Error uploading cheque image for cheque {cheque.id}: {e}")
                    # Don't fail the entire operation, just log the error
            
            logger.info(f"✅ Created cheque: {cheque.id} with data: {cheque_data}")
            return cheque
            
        logger.info("❌ No cheque data found")
        return None

    def perform_create(self, serializer):
        # Handle cheque data manually since it comes from multipart form
        cheque = self.handle_cheque_data(self.request)
        instance = serializer.save(
            account=self.request.user.account, 
            created_by=self.request.user,
            cheque=cheque
        )
        log_activity(self.request.user, self.request.user.account, f"تم إنشاء دفعة بمبلغ {instance.amount}", 'Payment', str(instance.id))

    def perform_update(self, serializer):
        # Handle cheque data for updates
        cheque = self.handle_cheque_data(self.request)
        instance = serializer.save(account=self.request.user.account, cheque=cheque)
        log_activity(self.request.user, self.request.user.account, f"تم تعديل دفعة بمبلغ {instance.amount}", 'Payment', str(instance.id))

    def perform_destroy(self, instance):
        log_activity(self.request.user, self.request.user.account, f"تم حذف دفعة بمبلغ {instance.amount}", 'Payment', str(instance.id))
        instance.delete()


class RecipientViewSet(viewsets.ModelViewSet):
    serializer_class = RecipientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'school_fee', 'payment_type']
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        account = self.request.user.account
        queryset = Recipient.objects.filter(account=account).select_related(
            'cheque',
            'student', 
            'school_fee', 
            'student__school_class',
            'created_by',
            'school_year'
        ).prefetch_related(
            'student__school_class',
            'documents'
        )

        school_year_param = self.request.query_params.get('school_year')
        if school_year_param == 'current':
            active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
            if active_year:
                queryset = queryset.filter(school_year=active_year)

        return queryset

    def get_serializer_context(self):
        """Add request context to serializer for URL generation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve to ensure all related data is properly loaded
        """
        instance = self.get_object()
        
        # Force reload the instance with proper relations
        instance = Recipient.objects.select_related(
            'cheque',
            'student',
            'school_fee',
            'student__school_class',
            'created_by',
            'school_year'
        ).prefetch_related('documents').get(pk=instance.pk)
        
        # Debug logging
        logger.info(f"🔍 Retrieved recipient {instance.id}")
        logger.info(f"🔍 Payment type: {instance.payment_type}")
        logger.info(f"🔍 Created by: {instance.created_by}")
        logger.info(f"🔍 School year: {instance.school_year}")
        logger.info(f"🔍 Cheque object: {instance.cheque}")
        if instance.cheque:
            logger.info(f"🔍 Cheque details: {instance.cheque.__dict__}")
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def handle_cheque_data(self, request):
        """Handle cheque data from multipart form data - Enhanced version"""
        logger.info("🔍 Debug: Incoming request data:", dict(request.data))
        logger.info("🔍 Debug: Incoming files:", dict(request.FILES))
        
        # Handle both nested and flat field formats
        cheque_data = {}
        
        # Try nested format first (cheque_details.field_name)
        nested_fields = {
            'bank_number': request.data.get('cheque_details.bank_number'),
            'branch_number': request.data.get('cheque_details.branch_number'), 
            'account_number': request.data.get('cheque_details.account_number'),
            'cheque_date': request.data.get('cheque_details.cheque_date'),
            'cheque_number': request.data.get('cheque_details.cheque_number'),
            'description': request.data.get('cheque_details.description')
        }
        
        # Try flat format as fallback
        flat_fields = {
            'bank_number': request.data.get('bankNumber'),
            'branch_number': request.data.get('branchNumber'),
            'account_number': request.data.get('accountNumber'), 
            'cheque_date': request.data.get('chequeDueDate'),
            'cheque_number': request.data.get('chequeNumber'),
            'description': request.data.get('description') or request.data.get('note')
        }
        
        # Use nested if available, otherwise fall back to flat
        for field in ['bank_number', 'branch_number', 'account_number', 'cheque_date', 'cheque_number', 'description']:
            if nested_fields[field]:
                cheque_data[field] = nested_fields[field]
            elif flat_fields[field]:
                cheque_data[field] = flat_fields[field]
        
        logger.info("🔍 Debug: Processed cheque data:", cheque_data)
        
        # Only create cheque if at least one field has data
        if any(value for value in cheque_data.values() if value):
            cheque = ChequeDetail.objects.create(**cheque_data)
            
            # Handle image upload with multiple possible field names
            image_file = (
                request.FILES.get('cheque_details.cheque_image') or 
                request.FILES.get('chequeImage') or
                request.FILES.get('cheque_image')
            )
            
            if image_file:
                try:
                    cheque.cheque_image = image_file
                    cheque.save()
                    logger.info(f"✅ Successfully uploaded cheque image for cheque {cheque.id}")
                except Exception as e:
                    logger.error(f"❌ Error uploading cheque image for cheque {cheque.id}: {e}")
                    # Don't fail the entire operation, just log the error
                    
            logger.info(f"✅ Created cheque: {cheque.id} with data: {cheque_data}")
            return cheque
            
        logger.info("❌ No cheque data found")
        return None
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def not_received(self, request):
        """Custom action to get not received recipients with cheque details"""
        queryset = self.get_queryset().filter(received=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def with_cheques(self, request):
        """Custom action to get only recipients that have cheque details"""
        queryset = self.get_queryset().filter(cheque__isnull=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        logger.info("🔍 Creating recipient with data:", dict(self.request.data))
        cheque = self.handle_cheque_data(self.request)
        instance = serializer.save(
            account=self.request.user.account, 
            created_by=self.request.user, 
            cheque=cheque
        )
        logger.info(f"✅ Created recipient: {instance.id} with cheque: {instance.cheque}")
        log_activity(self.request.user, self.request.user.account, f"تم إنشاء سند صرف بمبلغ {instance.amount}", 'Recipient', str(instance.id))

    def perform_update(self, serializer):
        logger.info("🔍 Updating recipient with data:", dict(self.request.data))
        instance = self.get_object()
        
        # Handle cheque data for updates
        cheque = self.handle_cheque_data(self.request)
        
        # If we have new cheque data, use it; otherwise keep existing
        if cheque:
            # If there was an existing cheque and we're creating a new one, 
            # we might want to update the existing one instead
            if instance.cheque:
                # Update existing cheque
                for field in ['bank_number', 'branch_number', 'account_number', 'cheque_date', 'cheque_number', 'description']:
                    if hasattr(cheque, field):
                        setattr(instance.cheque, field, getattr(cheque, field))
                
                # Handle image update
                if cheque.cheque_image:
                    instance.cheque.cheque_image = cheque.cheque_image
                
                instance.cheque.save()
                cheque.delete()  # Remove the temporary cheque we created
                cheque = instance.cheque
            
        updated_instance = serializer.save(
            account=self.request.user.account, 
            cheque=cheque if cheque else instance.cheque
        )
        logger.info(f"✅ Updated recipient: {updated_instance.id} with cheque: {updated_instance.cheque}")
        log_activity(self.request.user, self.request.user.account, f"تم تعديل سند صرف بمبلغ {updated_instance.amount}", 'Recipient', str(updated_instance.id))


# Additional payment document management endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_payment_document(request, payment_id):
    """Upload a document for a specific payment"""
    try:
        payment = Payment.objects.get(id=payment_id, account=request.user.account)
        
        document_type = request.data.get('document_type')
        document_file = request.FILES.get('document')
        description = request.data.get('description', '')
        
        if not document_type or not document_file:
            return Response({
                'error': 'نوع الوثيقة والملف مطلوبان'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create document
        document = PaymentDocument.objects.create(
            payment=payment,
            document_type=document_type,
            document=document_file,
            description=description,
            uploaded_by=request.user
        )
        
        serializer = PaymentDocumentSerializer(document, context={'request': request})
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم رفع وثيقة {document.get_document_type_display()} للدفعة {payment.number}",
            related_model='PaymentDocument',
            related_id=str(document.id)
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Payment.DoesNotExist:
        return Response({
            'error': 'الدفعة غير موجودة'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء رفع الوثيقة',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_recipient_document(request, recipient_id):
    """Upload a document for a specific recipient"""
    try:
        recipient = Recipient.objects.get(id=recipient_id, account=request.user.account)
        
        document_type = request.data.get('document_type')
        document_file = request.FILES.get('document')
        description = request.data.get('description', '')
        
        if not document_type or not document_file:
            return Response({
                'error': 'نوع الوثيقة والملف مطلوبان'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create document
        document = PaymentDocument.objects.create(
            recipient=recipient,
            document_type=document_type,
            document=document_file,
            description=description,
            uploaded_by=request.user
        )
        
        serializer = PaymentDocumentSerializer(document, context={'request': request})
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم رفع وثيقة {document.get_document_type_display()} لسند الصرف {recipient.number}",
            related_model='PaymentDocument',
            related_id=str(document.id)
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Recipient.DoesNotExist:
        return Response({
            'error': 'سند الصرف غير موجود'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء رفع الوثيقة',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_payment_document(request, document_id):
    """Delete a payment document"""
    try:
        document = PaymentDocument.objects.get(
            id=document_id
        )
        
        # Verify user has access to this document
        if document.payment and document.payment.account != request.user.account:
            return Response({
                'error': 'غير مصرح بالوصول'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if document.recipient and document.recipient.account != request.user.account:
            return Response({
                'error': 'غير مصرح بالوصول'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Delete from S3
        if document.document:
            s3_manager = S3FileManager()
            s3_manager.delete_file(document.document.name)
        
        doc_type = document.get_document_type_display()
        target_name = ""
        if document.payment:
            target_name = f"الدفعة {document.payment.number}"
        elif document.recipient:
            target_name = f"سند الصرف {document.recipient.number}"
        
        document.delete()
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم حذف وثيقة {doc_type} من {target_name}",
            related_model='PaymentDocument',
            related_id=str(document.id)
        )
        
        return Response({
            'message': 'تم حذف الوثيقة بنجاح'
        }, status=status.HTTP_200_OK)
        
    except PaymentDocument.DoesNotExist:
        return Response({
            'error': 'الوثيقة غير موجودة'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء حذف الوثيقة'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_cheque_image(request, cheque_id):
    """Delete a cheque image"""
    try:
        cheque = ChequeDetail.objects.get(id=cheque_id)
        
        # Verify user has access to this cheque
        # Check if cheque belongs to a payment or recipient in user's account
        payment_access = Payment.objects.filter(cheque=cheque, account=request.user.account).exists()
        recipient_access = Recipient.objects.filter(cheque=cheque, account=request.user.account).exists()
        
        if not (payment_access or recipient_access):
            return Response({
                'error': 'غير مصرح بالوصول'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Delete from S3
        if cheque.cheque_image:
            s3_manager = S3FileManager()
            s3_manager.delete_file(cheque.cheque_image.name)
            
            # Clear the field
            cheque.cheque_image = None
            cheque.save()
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم حذف صورة الشيك {cheque.cheque_number or cheque.id}",
            related_model='ChequeDetail',
            related_id=str(cheque.id)
        )
        
        return Response({
            'message': 'تم حذف صورة الشيك بنجاح'
        }, status=status.HTTP_200_OK)
        
    except ChequeDetail.DoesNotExist:
        return Response({
            'error': 'الشيك غير موجود'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء حذف صورة الشيك'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_dashboard_stats(request):
    """Get dashboard statistics for payments"""
    account = request.user.account
    
    try:
        from django.db.models import Sum, Count, Avg
        from datetime import datetime, timedelta
        
        # Date filters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        payments_qs = Payment.objects.filter(account=account)
        recipients_qs = Recipient.objects.filter(account=account)
        
        # Apply date filters if provided
        if start_date:
            payments_qs = payments_qs.filter(date__gte=start_date)
            recipients_qs = recipients_qs.filter(date__gte=start_date)
        if end_date:
            payments_qs = payments_qs.filter(date__lte=end_date)
            recipients_qs = recipients_qs.filter(date__lte=end_date)
        
        # Payment statistics
        payment_stats = payments_qs.aggregate(
            total_payments=Count('id'),
            total_amount_paid=Sum('amount'),
            avg_payment=Avg('amount')
        )
        
        # Recipient statistics  
        recipient_stats = recipients_qs.aggregate(
            total_recipients=Count('id'),
            total_amount_received=Sum('amount'),
            avg_receipt=Avg('amount'),
            pending_receipts=Count('id', filter=Q(received=False))
        )
        
        # Cheque statistics
        cheque_stats = {
            'total_cheques': ChequeDetail.objects.filter(
                Q(payment__account=account) | Q(recipients__account=account)
            ).distinct().count(),
            'cheques_with_images': ChequeDetail.objects.filter(
                Q(payment__account=account) | Q(recipients__account=account),
                cheque_image__isnull=False
            ).distinct().count()
        }
        
        return Response({
            'payment_stats': payment_stats,
            'recipient_stats': recipient_stats,
            'cheque_stats': cheque_stats
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء جلب إحصائيات المدفوعات',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

