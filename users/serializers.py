# serializers.py - Simplified without UIPreferencesSerializer

from datetime import datetime, time, timezone
from pytz import timezone as pytz_timezone, UTC
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import logging
from rest_framework import serializers
from .models import CustomUser, Account
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode

logger = logging.getLogger(__name__)


class AccountUpdateSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    ui_preferences = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = [
            'school_name', 'phone_number', 'email',
            'address', 'logo', 'logo_url', 'start_school_date', 'end_school_date',
            'ui_preferences'  # Only include ui_preferences, not the individual fields
        ]
    
    def get_logo_url(self, obj):
        """Generate URL for logo with error handling"""
        if not obj.logo:
            return None
        
        try:
            url = obj.logo.url
            logger.info(f"Django generated URL for account {obj.id}: {url}")
            return url
        except Exception as e:
            logger.error(f"Error getting Django URL for account {obj.id}: {e}")
            try:
                file_path = obj.logo.name
                if not file_path.startswith('media/'):
                    file_path = f"media/{file_path}"
                base_url = "https://daftar-noon.s3.il-central-1.amazonaws.com/"
                manual_url = f"{base_url}{file_path}"
                logger.info(f"Manual URL for account {obj.id}: {manual_url}")
                return manual_url
            except Exception as manual_error:
                logger.error(f"Manual URL generation failed for account {obj.id}: {manual_error}")
                return None
    
    def get_ui_preferences(self, obj):
        """Get organized UI preferences"""
        return obj.get_enabled_menu_items()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        if not user.account:
            raise serializers.ValidationError("المستخدم غير مرتبط بحساب صالح. يرجى التواصل مع المسؤول.")
        
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        token['account_id'] = user.account_id

        # Get current time in Israel timezone
        israel = pytz_timezone('Asia/Jerusalem')
        now_israel = datetime.now(israel)
        naive_end = datetime.combine(now_israel.date(), time(23, 59, 59))
        end_of_day_israel = israel.localize(naive_end)
        now_utc = now_israel.astimezone(UTC)
        end_utc = end_of_day_israel.astimezone(UTC)
        token.set_exp(from_time=now_utc, lifetime=end_utc - now_utc)

        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        if not self.user.account:
            raise serializers.ValidationError("المستخدم غير مرتبط بحساب صالح. يرجى التواصل مع المسؤول.")
        
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        account = self.user.account

        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'account_id': self.user.account_id,
            'full_name': full_name,
        }
        data['role'] = self.user.role
        data['school'] = {
            'name': account.school_name or 'غير محدد',
            'address': account.address or '',
            'email': account.email or '',
            'phone_number': account.phone_number or '',
            'logo': self._get_logo_url(account),
        }
        # Include UI preferences from database
        data['ui_preferences'] = account.get_enabled_menu_items()
        return data
    
    def _get_logo_url(self, account):
        """Helper method to get logo URL"""
        if not account.logo:
            return None
        
        try:
            return account.logo.url
        except Exception as e:
            logger.error(f"Error getting logo URL for account {account.id}: {e}")
            try:
                file_path = account.logo.name
                if not file_path.startswith('media/'):
                    file_path = f"media/{file_path}"
                return f"https://daftar-noon.s3.il-central-1.amazonaws.com/{file_path}"
            except Exception:
                return None


class MeSerializer(serializers.ModelSerializer):
    account = AccountUpdateSerializer()
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'account', 'full_name', 'phone']


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField()

    def validate(self, data):
        try:
            uid = urlsafe_base64_decode(data['uid']).decode()
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            raise serializers.ValidationError("الرابط غير صالح")

        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError("رمز إعادة التعيين غير صالح أو منتهي الصلاحية")

        user.set_password(data['new_password'])
        user.save()
        return data


class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        if len(value) < 8 or not any(c.isdigit() for c in value) or not any(c.isalpha() for c in value):
            raise serializers.ValidationError("كلمة المرور يجب أن تكون 8 أحرف على الأقل وتحتوي على رقم وحرف")
        return value