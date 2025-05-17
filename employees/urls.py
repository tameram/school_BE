from django.urls import path
from .views import EmployeeListCreateView, EmployeeRetrieveUpdateView, EmployeeHistoryViewSet


urlpatterns = [
    path('', EmployeeListCreateView.as_view(), name='employee-list-create'),
    path('employee-history', EmployeeHistoryViewSet, basename='employee-history'),
    path('<uuid:id>/', EmployeeRetrieveUpdateView.as_view(), name='employee-detail-update'),
]
