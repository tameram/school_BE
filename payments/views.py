from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser
from settings_data.models import SchoolYear
from .models import PaymentType, BankTransferDetail, ChequeDetail, Payment, Recipient
from .serializers import (
    PaymentTypeSerializer,
    BankTransferDetailSerializer,
    ChequeDetailSerializer,
    PaymentSerializer,
    RecipientSerializer
)
from logs.utils import log_activity
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated


class PaymentTypeViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentTypeSerializer

    def get_queryset(self):
        return PaymentType.objects.filter(account=self.request.user.account)

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


class NotReceivedRecipientList(ListAPIView):
    serializer_class = RecipientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Recipient.objects.filter(
            account=user.account, 
            received=False
        ).select_related('cheque', 'student', 'school_fee')


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        account = self.request.user.account
        # ✅ CRITICAL: Include cheque in select_related for proper serialization
        queryset = Payment.objects.filter(account=account).select_related(
            'cheque',  # This is essential for proper cheque serialization
            'recipient_employee', 
            'recipient_bus', 
            'recipient_authorized',
            'authorized_payer',
            'school_year'
        )

        school_year_param = self.request.query_params.get('school_year')
        if school_year_param == 'current':
            active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
            if active_year:
                queryset = queryset.filter(school_year=active_year)
        return queryset

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
        """Handle cheque data from multipart form data"""
        cheque_fields = ['bank_number', 'branch_number', 'account_number', 'cheque_date', 'cheque_number']
        cheque_data = {f: request.data.get(f'cheque_details.{f}') for f in cheque_fields}
        
        # Only create cheque if at least one field has data
        if any(cheque_data.values()):
            cheque = ChequeDetail.objects.create(**cheque_data)
            if 'cheque_details.cheque_image' in request.FILES:
                cheque.cheque_image = request.FILES['cheque_details.cheque_image']
                cheque.save()
            return cheque
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
    parser_classes = (MultiPartParser, FormParser)  # Add this line

    def get_queryset(self):
        account = self.request.user.account
        queryset = Recipient.objects.filter(account=account).select_related(
            'cheque', 'student', 'school_fee', 'student__school_class'
        )

        school_year_param = self.request.query_params.get('school_year')
        if school_year_param == 'current':
            active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
            if active_year:
                queryset = queryset.filter(school_year=active_year)

        return queryset

    def handle_cheque_data(self, request):
        """Handle cheque data from multipart form data - FIXED VERSION"""
        print("🔍 Debug: Incoming request data:", dict(request.data))  # Debug line
        
        # ✅ FIX: Handle both nested and flat field formats
        cheque_data = {}
        
        # Try nested format first (cheque_details.field_name)
        nested_fields = {
            'bank_number': request.data.get('cheque_details.bank_number'),
            'branch_number': request.data.get('cheque_details.branch_number'), 
            'account_number': request.data.get('cheque_details.account_number'),
            'cheque_date': request.data.get('cheque_details.cheque_date'),
            'cheque_number': request.data.get('cheque_details.cheque_number'),
            'description': request.data.get('cheque_details.description')  # ✅ Added this
        }
        
        # Try flat format as fallback (direct field names)
        flat_fields = {
            'bank_number': request.data.get('bankNumber'),
            'branch_number': request.data.get('branchNumber'),
            'account_number': request.data.get('accountNumber'), 
            'cheque_date': request.data.get('chequeDueDate'),
            'cheque_number': request.data.get('chequeNumber'),
            'description': request.data.get('description') or request.data.get('note')  # ✅ Added this
        }
        
        # Use nested if available, otherwise fall back to flat
        for field in ['bank_number', 'branch_number', 'account_number', 'cheque_date', 'cheque_number', 'description']:
            if nested_fields[field]:
                cheque_data[field] = nested_fields[field]
            elif flat_fields[field]:
                cheque_data[field] = flat_fields[field]
        
        print("🔍 Debug: Processed cheque data:", cheque_data)  # Debug line
        
        # Only create cheque if at least one field has data
        if any(value for value in cheque_data.values() if value):
            cheque = ChequeDetail.objects.create(**cheque_data)
            
            # Handle image upload
            image_file = (request.FILES.get('cheque_details.cheque_image') or 
                         request.FILES.get('chequeImage'))
            if image_file:
                cheque.cheque_image = image_file
                cheque.save()
                
            print("✅ Created cheque:", cheque.id, "with data:", cheque_data)  # Debug line
            return cheque
            
        print("❌ No cheque data found")  # Debug line
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
        print("🔍 Creating recipient with data:", dict(self.request.data))  # Debug line
        cheque = self.handle_cheque_data(self.request)
        instance = serializer.save(
            account=self.request.user.account, 
            created_by=self.request.user, 
            cheque=cheque
        )
        print("✅ Created recipient:", instance.id, "with cheque:", instance.cheque)  # Debug line
        log_activity(self.request.user, self.request.user.account, f"تم إنشاء سند صرف بمبلغ {instance.amount}", 'Recipient', str(instance.id))

    def perform_update(self, serializer):
        print("🔍 Updating recipient with data:", dict(self.request.data))  # Debug line
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
                instance.cheque.save()
                cheque.delete()  # Remove the temporary cheque we created
                cheque = instance.cheque
            
        updated_instance = serializer.save(
            account=self.request.user.account, 
            cheque=cheque if cheque else instance.cheque
        )
        print("✅ Updated recipient:", updated_instance.id, "with cheque:", updated_instance.cheque)  # Debug line
        log_activity(self.request.user, self.request.user.account, f"تم تعديل سند صرف بمبلغ {updated_instance.amount}", 'Recipient', str(updated_instance.id))
        