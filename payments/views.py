from rest_framework import viewsets, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser
from .models import PaymentType, BankTransferDetail, ChequeDetail, Payment, Recipient
from .serializers import (
    PaymentTypeSerializer,
    BankTransferDetailSerializer,
    ChequeDetailSerializer,
    PaymentSerializer,
    RecipientSerializer
)
from logs.utils import log_activity


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


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return Payment.objects.filter(account=self.request.user.account)

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
        return Recipient.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(self.request.user, self.request.user.account, f"تم إنشاء سند صرف بمبلغ {instance.amount}", 'Recipient', str(instance.id))

    def perform_update(self, serializer):
        instance = serializer.save(account=self.request.user.account)
        log_activity(self.request.user, self.request.user.account, f"تم تعديل سند صرف بمبلغ {instance.amount}", 'Recipient', str(instance.id))

    def perform_destroy(self, instance):
        log_activity(self.request.user, self.request.user.account, f"تم حذف سند صرف بمبلغ {instance.amount}", 'Recipient', str(instance.id))
        instance.delete()
