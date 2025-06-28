from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeListCreateView,
    EmployeeRetrieveUpdateView,
    EmployeePaymentCreateView,
    EmployeeVirtualTransactionViewSet,
    EmployeeHistoryViewSet,
    upload_employee_document,
    delete_employee_document,
    employee_dashboard_stats,
)

router = DefaultRouter()
router.register(r'employee-virtual-transactions', EmployeeVirtualTransactionViewSet, basename='employee-virtual-transactions')
router.register(r'employee-history', EmployeeHistoryViewSet, basename='employee-history')

urlpatterns = [
    # Employees
    path('', EmployeeListCreateView.as_view(), name='employee-list-create'),
    path('<uuid:id>/', EmployeeRetrieveUpdateView.as_view(), name='employee-detail-update'),
    path('<uuid:employee_id>/add-payment/', EmployeePaymentCreateView.as_view(), name='employee-add-payment'),
    path('dashboard-stats/', employee_dashboard_stats, name='employee-dashboard-stats'),
    
    # Document management
    path('documents/upload/<uuid:employee_id>/', upload_employee_document, name='upload_employee_document'),
    path('documents/delete/<uuid:document_id>/', delete_employee_document, name='delete_employee_document'),
]

urlpatterns += router.urls

