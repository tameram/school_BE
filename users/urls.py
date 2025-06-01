# accounts/urls.py
from django.urls import path
from .views import CustomLoginView, AccountUpdateView, MeView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('account/', AccountUpdateView.as_view(), name='account_update'),  
    path('me/', MeView.as_view(), name='me')
]
