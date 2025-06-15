# accounts/views.py
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, MeSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Account
from .serializers import AccountUpdateSerializer
from logs.utils import log_activity
from rest_framework import serializers


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

User = get_user_model()
class AccountUsersListView(APIView):
    """
    Get all users that belong to the current user's account
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get all users from the same account
            users = User.objects.filter(
                account=request.user.account,
                is_active=True
            ).values(
                'id', 
                'username', 
                'first_name', 
                'last_name', 
                'email', 
                'role'
            )
            
            # Format the response for frontend consumption
            formatted_users = []
            for user in users:
                display_name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
                if not display_name:
                    display_name = user['username']
                
                formatted_users.append({
                    'id': str(user['id']),
                    'username': user['username'],
                    'display_name': display_name,
                    'email': user['email'],
                    'role': user['role']
                })
            
            return Response(formatted_users, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': 'Failed to fetch users'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
    

class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        if len(value) < 8 or not any(c.isdigit() for c in value) or not any(c.isalpha() for c in value):
            raise serializers.ValidationError("كلمة المرور يجب أن تكون 8 أحرف على الأقل وتحتوي على رقم وحرف")
        return value

class AuthenticatedPasswordResetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({"message": "تم تغيير كلمة المرور بنجاح"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    