from rest_framework import generics
from .models import Student, SchoolClass, StudentHistory, Bus
from .serializers import StudentSerializer, SchoolClassListSerializer, SchoolClassDetailSerializer, StudentHistorySerializer, BusSerializer
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend


class BusListCreateView(generics.ListCreateAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer

class BusRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    lookup_field = 'id'

class StudentListCreateView(generics.ListCreateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_archived', 'account']
    ordering_fields = ['date_of_registration']

class StudentRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    lookup_field = 'id'


class SchoolClassListCreateView(generics.ListCreateAPIView):
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassListSerializer

class SchoolClassRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassDetailSerializer
    lookup_field = 'id'

class StudentHistoryListCreateView(generics.ListCreateAPIView):
    queryset = StudentHistory.objects.all()
    serializer_class = StudentHistorySerializer

class StudentHistoryDetailView(generics.RetrieveAPIView):
    queryset = StudentHistory.objects.all()
    serializer_class = StudentHistorySerializer
    lookup_field = 'id'