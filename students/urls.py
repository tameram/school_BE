from django.urls import path
from .views import StudentListCreateView, StudentRetrieveUpdateView

urlpatterns = [
    path('', StudentListCreateView.as_view(), name='student-list-create'),
    path('<uuid:id>/', StudentRetrieveUpdateView.as_view(), name='student-detail-update'),
]
