from datetime import datetime, time, timezone
from pytz import timezone as pytz_timezone, UTC
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import logging
from rest_framework import serializers
from .models import CustomUser
from .models import Account

logger = logging.getLogger(__name__)


class AccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            'school_name', 'phone_number', 'email',
            'address', 'logo', 'start_school_date', 'end_school_date'
        ]

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['role'] = user.role
        token['account_id'] = user.account_id

        # Get current time in Israel timezone
        israel = pytz_timezone('Asia/Jerusalem')
        now_israel = datetime.now(israel)

        # Localize end of day
        naive_end = datetime.combine(now_israel.date(), time(23, 59, 59))
        end_of_day_israel = israel.localize(naive_end)
        now_utc = now_israel.astimezone(UTC)
        end_utc = end_of_day_israel.astimezone(UTC)

        # Set token expiration
        token.set_exp(from_time=now_utc, lifetime=end_utc - now_utc)

        return token

    def validate(self, attrs):
        data = super().validate(attrs)  # This sets self.user

        account = self.user.account  # ✅ Now safe to use
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'account_id': self.user.account_id,
        }
        data['role'] = self.user.role
        data['school'] = {
            'name': account.school_name,
            'address': account.address,
            'email': account.email,
            'phone_number': account.phone_number,
            'logo': account.logo.url if account.logo else None,
        }
        return data
    
class MeSerializer(serializers.ModelSerializer):
    account = AccountUpdateSerializer()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'account']


