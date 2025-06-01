# accounts/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, MeSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Account
from .serializers import AccountUpdateSerializer


class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# accounts/views.py


class AccountUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = request.user.account
        serializer = AccountUpdateSerializer(account)
        return Response(serializer.data)

    def put(self, request):
        account = request.user.account
        serializer = AccountUpdateSerializer(account, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)
    
