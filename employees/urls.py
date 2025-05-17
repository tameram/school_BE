from django.urls import path
from .views import EmployeeListCreateView, EmployeeRetrieveUpdateView

urlpatterns = [
    path('', EmployeeListCreateView.as_view(), name='employee-list-create'),
    path('<uuid:id>/', EmployeeRetrieveUpdateView.as_view(), name='employee-detail-update'),
]
