from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import EmployeeType, AuthorizedPayer, SchoolFee
from .serializers import EmployeeTypeSerializer, AuthorizedPayerSerializer, SchoolFeeSerializer

class EmployeeTypeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeType.objects.all()
    serializer_class = EmployeeTypeSerializer

    def get_queryset(self):
        return EmployeeType.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        serializer.save(account=self.request.user.account, created_by=self.request.user)


class AuthorizedPayerViewSet(viewsets.ModelViewSet):
    queryset = EmployeeType.objects.all()
    serializer_class = AuthorizedPayerSerializer

    def get_queryset(self):
        return AuthorizedPayer.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        serializer.save(account=self.request.user.account, created_by=self.request.user)


class SchoolFeeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeType.objects.all()
    serializer_class = SchoolFeeSerializer

    def get_queryset(self):
        return SchoolFee.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        serializer.save(account=self.request.user.account, created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(account=self.request.user.account)

    @action(detail=False, methods=['get', 'put'], url_path='default')
    def default_fee(self, request):
        # GET: retrieve the default school fee for this account
        if request.method == 'GET':
            try:
                fee = SchoolFee.objects.get(account=request.user.account, school_class__isnull=True, student__isnull=True)
                serializer = self.get_serializer(fee)
                return Response(serializer.data)
            except SchoolFee.DoesNotExist:
                return Response({"detail": "No default fee found."}, status=404)

        # PUT: update or create default school fee per account
        if request.method == 'PUT':
            fee, _ = SchoolFee.objects.get_or_create(
                account=request.user.account,
                school_class=None,
                student=None,
                defaults={'created_by': request.user}
            )
            serializer = self.get_serializer(fee, data=request.data)
            if serializer.is_valid():
                serializer.save(account=request.user.account)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
