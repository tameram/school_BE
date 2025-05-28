from rest_framework import viewsets
from .models import EmployeeType, AuthorizedPayer, SchoolFee
from .serializers import (
    EmployeeTypeSerializer, AuthorizedPayerSerializer, SchoolFeeSerializer
)
from rest_framework.response import Response
from rest_framework.decorators import action

class EmployeeTypeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeType.objects.all()
    serializer_class = EmployeeTypeSerializer

class AuthorizedPayerViewSet(viewsets.ModelViewSet):
    queryset = AuthorizedPayer.objects.all()
    serializer_class = AuthorizedPayerSerializer

class SchoolFeeViewSet(viewsets.ModelViewSet):
    queryset = SchoolFee.objects.all()
    serializer_class = SchoolFeeSerializer

    @action(detail=False, methods=['get', 'put'], url_path='default')
    def default_fee(self, request):
        # GET: retrieve the default school fee
        if request.method == 'GET':
            try:
                fee = SchoolFee.objects.get(school_class__isnull=True, student__isnull=True)
                serializer = self.get_serializer(fee)
                return Response(serializer.data)
            except SchoolFee.DoesNotExist:
                return Response({"detail": "No default fee found."}, status=404)

        # PUT: update or create the default school fee
        if request.method == 'PUT':
            fee, _ = SchoolFee.objects.get_or_create(school_class=None, student=None)
            serializer = self.get_serializer(fee, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
