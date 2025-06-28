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

