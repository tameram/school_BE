from rest_framework import generics
from .models import Employee, EmployeeHistory
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import EmployeeSerializer, EmployeeHistorySerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated



class EmployeeListCreateView(generics.ListCreateAPIView):
    serializer_class = EmployeeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee_type']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Employee.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        serializer.save(account=self.request.user.account, created_by=self.request.user)

class EmployeeRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        return Employee.objects.filter(account=self.request.user.account)

    def perform_update(self, serializer):
        serializer.save(account=self.request.user.account)


class EmployeeHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeHistorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmployeeHistory.objects.filter(employee__account=self.request.user.account)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)