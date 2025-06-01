# accounts/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, MeSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Account
from .serializers import AccountUpdateSerializer
from logs.utils import log_activity


class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        response = super().post(request, *args, **kwargs)

        user = serializer.user  # ✅ use this instead of self.user

        if response.status_code == 200 and hasattr(user, 'account'):
            log_activity(
                user=user,
                account=user.account,
                note="تسجيل دخول المستخدم"
            )
        return response

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
    
