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



class NotReceivedRecipientList(ListAPIView):
    serializer_class = RecipientSerializer

    def get_queryset(self):
        user = self.request.user
        return Recipient.objects.filter(account=user.account, received=False)

class ChequeDetailViewSet(viewsets.ModelViewSet):
    queryset = ChequeDetail.objects.all()
    serializer_class = ChequeDetailSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        account = self.request.user.account
        queryset = Payment.objects.filter(account=account)

        school_year_param = self.request.query_params.get('school_year')
        if school_year_param == 'current':
            active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
            if active_year:
                queryset = queryset.filter(school_year=active_year)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(self.request.user, self.request.user.account, f"تم إنشاء دفعة بمبلغ {instance.amount}", 'Payment', str(instance.id))

    def perform_update(self, serializer):
        instance = serializer.save(account=self.request.user.account)
        log_activity(self.request.user, self.request.user.account, f"تم تعديل دفعة بمبلغ {instance.amount}", 'Payment', str(instance.id))

    def perform_destroy(self, instance):
        log_activity(self.request.user, self.request.user.account, f"تم حذف دفعة بمبلغ {instance.amount}", 'Payment', str(instance.id))
        instance.delete()


class RecipientViewSet(viewsets.ModelViewSet):
    serializer_class = RecipientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'school_fee', 'payment_type']

    def get_queryset(self):
        account = self.request.user.account
        queryset = Recipient.objects.filter(account=account)

        # Dynamic filtering for `?school_year=current`
        school_year_param = self.request.query_params.get('school_year')
        if school_year_param == 'current':
            active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
            if active_year:
                queryset = queryset.filter(school_year=active_year)

        return queryset

    def handle_cheque_data(self, request):
        cheque_fields = ['bank_number', 'branch_number', 'account_number', 'cheque_date']
        cheque_data = {f: request.data.get(f'cheque_details.{f}') for f in cheque_fields}
        if any(cheque_data.values()):
            cheque = ChequeDetail.objects.create(**cheque_data)
            if 'cheque_details.cheque_image' in request.FILES:
                cheque.cheque_image = request.FILES['cheque_details.cheque_image']
                cheque.save()
            return cheque
        return None
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def not_received(self, request):
        queryset = self.get_queryset().filter(received=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        cheque = self.handle_cheque_data(self.request)
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user, cheque=cheque)
        log_activity(self.request.user, self.request.user.account, f"تم إنشاء سند صرف بمبلغ {instance.amount}", 'Recipient', str(instance.id))

    def perform_update(self, serializer):
        cheque = self.handle_cheque_data(self.request)
        instance = serializer.save(account=self.request.user.account, cheque=cheque)
        log_activity(self.request.user, self.request.user.account, f"تم تعديل سند صرف بمبلغ {instance.amount}", 'Recipient', str(instance.id))
