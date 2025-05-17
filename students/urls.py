from django.urls import path
from .views import (
    StudentListCreateView, StudentRetrieveUpdateView,
    SchoolClassListCreateView, SchoolClassRetrieveUpdateView,
    StudentHistoryListCreateView, StudentHistoryDetailView
)

urlpatterns = [
    path('', StudentListCreateView.as_view(), name='student-list-create'),
    path('<uuid:id>/', StudentRetrieveUpdateView.as_view(), name='student-detail-update'),

    path('classes/', SchoolClassListCreateView.as_view(), name='class-list-create'),
    path('classes/<uuid:id>/', SchoolClassRetrieveUpdateView.as_view(), name='class-detail-update'),

     path('student-history/', StudentHistoryListCreateView.as_view(), name='student-history-list-create'),
    path('student-history/<uuid:id>/', StudentHistoryDetailView.as_view(), name='student-history-detail'),

]
