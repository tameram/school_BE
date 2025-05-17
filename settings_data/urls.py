from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeTypeViewSet, AuthorizedPayerViewSet, SchoolFeeViewSet

router = DefaultRouter()
router.register('employee-types', EmployeeTypeViewSet)
router.register('authorized-payers', AuthorizedPayerViewSet)
router.register('school-fees', SchoolFeeViewSet)

urlpatterns = router.urls
