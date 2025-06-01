from django.urls import path

from students.serializers import SchoolClassRetrieveUpdateDeleteView
from .views import (
    StudentListCreateView, StudentRetrieveUpdateView,
    SchoolClassListCreateView, SchoolClassRetrieveUpdateView,
    StudentHistoryListCreateView, StudentHistoryDetailView,
    BusListCreateView, BusRetrieveUpdateView, close_student_account
)

urlpatterns = [
    path('', StudentListCreateView.as_view(), name='student-list-create'),
    path('<uuid:id>/', StudentRetrieveUpdateView.as_view(), name='student-detail-update'),

    path('classes/', SchoolClassListCreateView.as_view(), name='class-list-create'),
    path('classes/<uuid:id>/', SchoolClassRetrieveUpdateDeleteView.as_view(), name='class-detail-update-delete'),

     path('student-history/', StudentHistoryListCreateView.as_view(), name='student-history-list-create'),
    path('student-history/<uuid:id>/', StudentHistoryDetailView.as_view(), name='student-history-detail'),

    path('buses/', BusListCreateView.as_view(), name='bus-list-create'),
    path('buses/<uuid:id>/', BusRetrieveUpdateView.as_view(), name='bus-detail'),

    path('close-account/<uuid:id>/', close_student_account, name='close-student-account'),


]
