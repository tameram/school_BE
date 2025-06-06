from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotReceivedRecipientList
from .views import (
    PaymentTypeViewSet,
    BankTransferDetailViewSet,
    ChequeDetailViewSet,PaymentViewSet, RecipientViewSet
)

router = DefaultRouter()
router.register('types', PaymentTypeViewSet, basename='payment-type')
router.register('bank-transfers', BankTransferDetailViewSet, basename='bank-transfer')
router.register('cheques', ChequeDetailViewSet, basename='cheque')
router.register('payments', PaymentViewSet, basename='payments')
path('recipients/not_received/', NotReceivedRecipientList, name='not-received-recipients'),
router.register('recipients', RecipientViewSet, basename='recipients')


urlpatterns = [
    path('', include(router.urls)),
]
