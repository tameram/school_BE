from rest_framework import viewsets
from .models import EmployeeType, AuthorizedPayer, SchoolFee
from .serializers import (
    EmployeeTypeSerializer, AuthorizedPayerSerializer, SchoolFeeSerializer
)

class EmployeeTypeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeType.objects.all()
    serializer_class = EmployeeTypeSerializer

class AuthorizedPayerViewSet(viewsets.ModelViewSet):
    queryset = AuthorizedPayer.objects.all()
    serializer_class = AuthorizedPayerSerializer

class SchoolFeeViewSet(viewsets.ModelViewSet):
    queryset = SchoolFee.objects.all()
    serializer_class = SchoolFeeSerializer
