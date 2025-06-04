# store/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreItemViewSet

router = DefaultRouter()
router.register(r'store-items', StoreItemViewSet, basename='inventory-item')  # ✅ fix is here

urlpatterns = [
    path('', include(router.urls)),
]
