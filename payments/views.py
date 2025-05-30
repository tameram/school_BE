from rest_framework import viewsets
from .models import PaymentType, BankTransferDetail, ChequeDetail, Payment, Recipient
from .serializers import (
    PaymentTypeSerializer,
    BankTransferDetailSerializer,
    ChequeDetailSerializer,
    PaymentSerializer, RecipientSerializer
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser


class PaymentTypeViewSet(viewsets.ModelViewSet):
    queryset = PaymentType.objects.all()
    serializer_class = PaymentTypeSerializer

class BankTransferDetailViewSet(viewsets.ModelViewSet):
    queryset = BankTransferDetail.objects.all()
    serializer_class = BankTransferDetailSerializer

class ChequeDetailViewSet(viewsets.ModelViewSet):
    queryset = ChequeDetail.objects.all()
    serializer_class = ChequeDetailSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    parser_classes = (MultiPartParser, FormParser)


class RecipientViewSet(viewsets.ModelViewSet):
    queryset = Recipient.objects.all()
    serializer_class = RecipientSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'school_fee', 'payment_type']