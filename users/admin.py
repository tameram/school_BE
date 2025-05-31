# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Account

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email','phone', 'account', 'role', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'account__name']
    ordering = ['username']

    fieldsets = UserAdmin.fieldsets + (
        (None, {
            'fields': ('account', 'role')
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Account)
