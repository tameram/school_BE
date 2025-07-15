import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from utils.file_handlers import general_documents_path
from utils.storage_backends import MediaStorage
from utils.file_handlers import logo_path


class Account(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    school_name = models.CharField(max_length=255, null=True, blank=True)
    
    # ✅ Updated to use S3 storage
    logo = models.ImageField(
        upload_to=logo_path,
        storage=MediaStorage(),
        null=True, 
        blank=True,
        help_text="School/Account logo"
    )
    
    start_school_date = models.DateField(null=True, blank=True)
    end_school_date = models.DateField(null=True, blank=True)
    join_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # ✅ NEW: UI Display Preferences
    # Financial Section
    show_financial_management = models.BooleanField(default=True, help_text="إدارة سندات الصرف")
    show_recipient_management = models.BooleanField(default=True, help_text="إدارة سندات القبض")
    show_payments_schedule = models.BooleanField(default=True, help_text="جدول الدفعات")
    show_outgoing_cheques = models.BooleanField(default=True, help_text="الشيكات الصادرة")
    
    # School Section
    show_students = models.BooleanField(default=True, help_text="الطلاب")
    show_staff = models.BooleanField(default=True, help_text="الموظفين")
    show_classes = models.BooleanField(default=True, help_text="الصفوف")
    show_buses = models.BooleanField(default=True, help_text="الحافلات")
    show_store = models.BooleanField(default=True, help_text="المستودع")
    show_archive = models.BooleanField(default=True, help_text="الأرشيف")
    
    # Administrative Section (only affects managers)
    show_logs = models.BooleanField(default=True, help_text="سجل التغييرات")
    show_settings = models.BooleanField(default=True, help_text="الإعدادات")
    
    # General Features
    show_password_reset = models.BooleanField(default=True, help_text="تعيين كلمة مرور جديدة")
    
    def get_enabled_menu_items(self):
        """Return a dictionary of enabled menu items for this account"""
        return {
            'financial': {
                'financial_management': self.show_financial_management,
                'recipient_management': self.show_recipient_management,
                'payments_schedule': self.show_payments_schedule,
                'outgoing_cheques': self.show_outgoing_cheques,
            },
            'school': {
                'students': self.show_students,
                'staff': self.show_staff,
                'classes': self.show_classes,
                'buses': self.show_buses,
                'store': self.show_store,
                'archive': self.show_archive,
            },
            'administrative': {
                'logs': self.show_logs,
                'settings': self.show_settings,
            },
            'general': {
                'password_reset': self.show_password_reset,
            }
        }
    
    def has_any_financial_features(self):
        """Check if account has any financial features enabled"""
        return any([
            self.show_financial_management,
            self.show_recipient_management,
            self.show_payments_schedule,
            self.show_outgoing_cheques,
        ])
    
    def has_any_school_features(self):
        """Check if account has any school features enabled"""
        return any([
            self.show_students,
            self.show_staff,
            self.show_classes,
            self.show_buses,
            self.show_store,
            self.show_archive,
        ])
    
    def has_any_admin_features(self):
        """Check if account has any admin features enabled"""
        return any([
            self.show_logs,
            self.show_settings,
        ])

    def __str__(self):
        return self.name or "Unnamed Account"


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    ROLE_CHOICES = (
        ('manager', 'Manager'),
        ('employee', 'Employee'),
    )
    is_active = models.BooleanField(default=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)

