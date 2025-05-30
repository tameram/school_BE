from rest_framework import generics
from .models import Employee, EmployeeHistory
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import EmployeeSerializer, EmployeeHistorySerializer
from rest_framework import viewsets


class EmployeeListCreateView(generics.ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

class EmployeeRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    lookup_field = 'id'


class EmployeeListCreateView(generics.ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee_type']

class EmployeeHistoryViewSet(viewsets.ModelViewSet):
    queryset = EmployeeHistory.objects.all()
    serializer_class = EmployeeHistorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee']