from django.urls import path
from .views import (
    AccountUsersListView, 
    CustomLoginView, 
    AccountUpdateView, 
    MeView, 
    AuthenticatedPasswordResetView,
    delete_account_logo,
    upload_account_logo,
    account_stats,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Authentication
    path('login/', CustomLoginView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('reset-password/', AuthenticatedPasswordResetView.as_view(), name='reset-password'),
    
    # Account management
    path('account/', AccountUpdateView.as_view(), name='account_update'),  
    path('account/logo/upload/', upload_account_logo, name='upload_account_logo'),
    path('account/logo/delete/', delete_account_logo, name='delete_account_logo'),
    path('account/stats/', account_stats, name='account_stats'),
    
    # User management
    path('me/', MeView.as_view(), name='me'),
    path('users/', AccountUsersListView.as_view(), name='account-users'),
]