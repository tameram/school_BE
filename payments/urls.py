from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotReceivedRecipientList,
    PaymentTypeViewSet,
    BankTransferDetailViewSet,
    ChequeDetailViewSet,
    PaymentViewSet, 
    RecipientViewSet,
    upload_payment_document,
    upload_recipient_document,
    delete_payment_document,
    delete_cheque_image,
    payment_dashboard_stats,
    payments_with_cheques,          # Add this import
)

router = DefaultRouter()
router.register('types', PaymentTypeViewSet, basename='payment-type')
router.register('bank-transfers', BankTransferDetailViewSet, basename='bank-transfer')
router.register('cheques', ChequeDetailViewSet, basename='cheque')
router.register('payments', PaymentViewSet, basename='payments')
router.register('recipients', RecipientViewSet, basename='recipients')

urlpatterns = [
    # Basic endpoints
    path('recipients/not_received/', NotReceivedRecipientList.as_view(), name='not-received-recipients'),
    path('dashboard-stats/', payment_dashboard_stats, name='payment-dashboard-stats'),
    
    # NEW: Cheque payments endpoints
    path('with-cheques/', payments_with_cheques, name='payments-with-cheques'),

    
    # Document management
    path('documents/payment/<uuid:payment_id>/', upload_payment_document, name='upload_payment_document'),
    path('documents/recipient/<uuid:recipient_id>/', upload_recipient_document, name='upload_recipient_document'),
    path('documents/delete/<uuid:document_id>/', delete_payment_document, name='delete_payment_document'),
    
    # Cheque image management
    path('cheques/<uuid:cheque_id>/delete-image/', delete_cheque_image, name='delete_cheque_image'),
    
    # Router URLs
    path('', include(router.urls)),
]