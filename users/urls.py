# accounts/urls.py
from django.urls import path
from .views import AccountUsersListView, CustomLoginView, AccountUpdateView, MeView, AuthenticatedPasswordResetView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('account/', AccountUpdateView.as_view(), name='account_update'),  
    path('me/', MeView.as_view(), name='me'),
    path('reset-password/', AuthenticatedPasswordResetView.as_view(), name='reset-password'),
    path('users/', AccountUsersListView.as_view(), name='account-users'),  # Add this line

    
]
