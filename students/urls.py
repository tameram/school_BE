# students/urls.py
from django.urls import path
from .views import (
    StudentListCreateView,
    StudentRetrieveUpdateView,
    SchoolClassListCreateView,
    SchoolClassRetrieveUpdateView,  # Make sure this is imported
    BusListCreateView,
    BusRetrieveUpdateView,
    students_with_open_accounts,
    close_student_account,
    StudentHistoryListCreateView,
    StudentHistoryDetailView,
)

urlpatterns = [
    # Students
    path('', StudentListCreateView.as_view(), name='student-list-create'),
    path('<uuid:id>/', StudentRetrieveUpdateView.as_view(), name='student-detail'),
    path('<uuid:id>/close-account/', close_student_account, name='close-student-account'),
    path('open-accounts/', students_with_open_accounts, name='students-open-accounts'),
    
    # Classes
    path('classes/', SchoolClassListCreateView.as_view(), name='class-list-create'),
    path('classes/<uuid:id>/', SchoolClassRetrieveUpdateView.as_view(), name='class-detail'),  # This should handle PUT
    
    # Buses
    path('buses/', BusListCreateView.as_view(), name='bus-list-create'),
    path('buses/<uuid:id>/', BusRetrieveUpdateView.as_view(), name='bus-detail'),
    
    # Student History
    path('history/', StudentHistoryListCreateView.as_view(), name='student-history-list'),
    path('history/<uuid:id>/', StudentHistoryDetailView.as_view(), name='student-history-detail'),
]