# accounts/admin.py
from django.contrib import admin
from .models import EmployeeType
from .models import SchoolYear

admin.site.register(EmployeeType)
admin.site.register(SchoolYear)
