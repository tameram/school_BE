# students/urls.py
from django.urls import path

from .views import (
    StudentListCreateView,
    StudentRetrieveUpdateView,
    SchoolClassListCreateView,
    SchoolClassRetrieveUpdateView,
    BusListCreateView,
    BusRetrieveUpdateView,
    delete_student_document,
    students_with_open_accounts,
    close_student_account,
    StudentHistoryListCreateView,
    StudentHistoryDetailView,
    upload_student_document,
)

urlpatterns = [
    # Students
    path('', StudentListCreateView.as_view(), name='student-list-create'),
    path('<uuid:id>/', StudentRetrieveUpdateView.as_view(), name='student-detail'),
    path('<uuid:id>/close-account/', close_student_account, name='close-student-account'),
    path('open-accounts/', students_with_open_accounts, name='students-open-accounts'),
    
    # Classes
    path('classes/', SchoolClassListCreateView.as_view(), name='class-list-create'),
    path('classes/<uuid:id>/', SchoolClassRetrieveUpdateView.as_view(), name='class-detail'),
    
    # Buses
    path('buses/', BusListCreateView.as_view(), name='bus-list-create'),
    path('buses/<uuid:id>/', BusRetrieveUpdateView.as_view(), name='bus-detail'),
    
    # Student History
    path('history/', StudentHistoryListCreateView.as_view(), name='student-history-list'),
    path('history/<uuid:id>/', StudentHistoryDetailView.as_view(), name='student-history-detail'),

    # Document management - these are function-based views, so NO .as_view()
    path('documents/upload/<uuid:student_id>/', upload_student_document, name='upload_student_document'),
    path('documents/delete/<uuid:document_id>/', delete_student_document, name='delete_student_document'),
]