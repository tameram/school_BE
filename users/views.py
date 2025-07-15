# views.py - Simplified without UIPreferencesView

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    CustomTokenObtainPairSerializer, 
    MeSerializer, 
    AccountUpdateSerializer,
    PasswordResetSerializer
)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, parsers
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from .models import Account
from logs.utils import log_activity
from utils.s3_utils import S3FileManager
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        response = super().post(request, *args, **kwargs)
        user = serializer.user

        if response.status_code == 200 and hasattr(user, 'account'):
            log_activity(
                user=user,
                account=user.account,
                note="تسجيل دخول المستخدم"
            )
        return response


class AccountUsersListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            users = User.objects.filter(
                account=request.user.account,
                is_active=True
            ).values(
                'id', 'username', 'first_name', 'last_name', 'email', 'role'
            )
            
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
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get(self, request):
        account = request.user.account
        serializer = AccountUpdateSerializer(account, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        account = request.user.account
        
        try:
            logo_file = request.FILES.get('logo')
            
            serializer = AccountUpdateSerializer(
                account, 
                data=request.data, 
                partial=True,
                context={'request': request}
            )
            
            if serializer.is_valid():
                updated_account = serializer.save()
                
                if logo_file:
                    try:
                        updated_account.logo = logo_file
                        updated_account.save(update_fields=['logo'])
                        logger.info(f"✅ Successfully uploaded logo for account {updated_account.id}")
                    except Exception as logo_error:
                        logger.error(f"❌ Error uploading logo for account {updated_account.id}: {logo_error}")
                
                log_activity(
                    user=request.user,
                    account=request.user.account,
                    note="تم تحديث بيانات الحساب",
                    related_model='Account',
                    related_id=str(updated_account.id)
                )
                
                response_serializer = AccountUpdateSerializer(
                    updated_account, 
                    context={'request': request}
                )
                return Response(response_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error updating account: {e}")
            return Response({
                'error': 'حدث خطأ أثناء تحديث الحساب',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request):
        return self.put(request)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class AuthenticatedPasswordResetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            
            log_activity(
                user=request.user,
                account=request.user.account,
                note="تم تغيير كلمة المرور",
                related_model='CustomUser',
                related_id=str(request.user.id)
            )
            
            return Response({"message": "تم تغيير كلمة المرور بنجاح"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account_logo(request):
    try:
        account = request.user.account
        
        if not account.logo:
            return Response({
                'message': 'لا يوجد شعار للحذف'
            }, status=status.HTTP_200_OK)
        
        s3_manager = S3FileManager()
        if account.logo:
            s3_manager.delete_file(account.logo.name)
            account.logo = None
            account.save(update_fields=['logo'])
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note="تم حذف شعار الحساب",
            related_model='Account',
            related_id=str(account.id)
        )
        
        return Response({'message': 'تم حذف الشعار بنجاح'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء حذف الشعار',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_account_logo(request):
    try:
        account = request.user.account
        logo_file = request.FILES.get('logo')
        
        if not logo_file:
            return Response({
                'error': 'لم يتم تحديد ملف الشعار'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
        if logo_file.content_type not in allowed_types:
            return Response({
                'error': 'نوع الملف غير مدعوم. يرجى استخدام JPG, PNG, أو GIF'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        max_size = 5 * 1024 * 1024  # 5MB
        if logo_file.size > max_size:
            return Response({
                'error': 'حجم الملف كبير جداً. الحد الأقصى 5 ميجابايت'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if account.logo:
            s3_manager = S3FileManager()
            s3_manager.delete_file(account.logo.name)
        
        account.logo = logo_file
        account.save(update_fields=['logo'])
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note="تم رفع شعار جديد للحساب",
            related_model='Account',
            related_id=str(account.id)
        )
        
        serializer = AccountUpdateSerializer(account, context={'request': request})
        return Response({
            'message': 'تم رفع الشعار بنجاح',
            'account': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error uploading logo: {e}")
        return Response({
            'error': 'حدث خطأ أثناء رفع الشعار',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def account_stats(request):
    try:
        account = request.user.account
        
        user_count = User.objects.filter(account=account, is_active=True).count()
        
        logo_info = {
            'has_logo': bool(account.logo),
            'logo_url': None
        }
        
        if account.logo:
            try:
                logo_info['logo_url'] = account.logo.url
            except Exception:
                logo_info['logo_url'] = None
        
        account_age_days = None
        if account.join_date:
            from datetime import date
            account_age_days = (date.today() - account.join_date).days
        
        stats = {
            'account_name': account.school_name or account.name,
            'user_count': user_count,
            'logo_info': logo_info,
            'account_age_days': account_age_days,
            'is_active': account.is_active,
            'has_contact_info': bool(account.phone_number or account.email),
            'has_address': bool(account.address),
            'school_dates_set': bool(account.start_school_date and account.end_school_date),
            'ui_preferences': account.get_enabled_menu_items()
        }
        
        return Response(stats, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء جلب إحصائيات الحساب',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)