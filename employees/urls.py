from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeListCreateView,
    EmployeeRetrieveUpdateView,
    EmployeePaymentCreateView,
    EmployeeVirtualTransactionViewSet,
)

router = DefaultRouter()
router.register(r'employee-virtual-transactions', EmployeeVirtualTransactionViewSet, basename='employee-virtual-transactions')

urlpatterns = [
    path('', EmployeeListCreateView.as_view(), name='employee-list-create'),
    path('<uuid:id>/', EmployeeRetrieveUpdateView.as_view(), name='employee-detail-update'),
    path('employees/<uuid:employee_id>/add-payment/', EmployeePaymentCreateView.as_view(), name='employee-add-payment'),
]

urlpatterns += router.urls  # ✅ This adds /api/employees/employee-virtual-transactions/
