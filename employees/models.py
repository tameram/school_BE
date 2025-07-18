from django.db import models
from settings_data.models import EmployeeType
from users.models import Account, CustomUser
import uuid
from django.core.exceptions import ValidationError
from utils.file_handlers import employee_documents_path
from utils.storage_backends import MediaStorage


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    employee_id = models.CharField(max_length=50, null=True, blank=True)
    
    birth_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    employee_type = models.ForeignKey(EmployeeType, on_delete=models.SET_NULL, null=True, blank=True)

    start_date = models.DateField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Updated to use S3 storage
    contract_pdf = models.FileField(
        upload_to=employee_documents_path,
        storage=MediaStorage(),
        null=True, 
        blank=True,
        help_text="Employee contract document"
    )
    
    # Additional file fields that might be useful
    profile_picture = models.ImageField(
        upload_to=employee_documents_path,
        storage=MediaStorage(),
        null=True,
        blank=True,
        help_text="Employee profile picture"
    )
    
    id_copy = models.FileField(
        upload_to=employee_documents_path,
        storage=MediaStorage(),
        null=True,
        blank=True,
        help_text="Copy of employee ID document"
    )
    
    note = models.TextField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='employees', null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        # Add unique constraint for employee_id within the same account
        constraints = [
            models.UniqueConstraint(
                fields=['employee_id', 'account'],
                condition=models.Q(employee_id__isnull=False) & ~models.Q(employee_id=''),
                name='unique_employee_id_per_account'
            )
        ]

    def clean(self):
        """
        Custom validation to ensure employee_id is unique within account
        """
        super().clean()
        
        if self.employee_id and self.account:
            # Check for duplicates
            existing = Employee.objects.filter(
                employee_id=self.employee_id,
                account=self.account
            )
            
            # Exclude current instance if updating
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            
            if existing.exists():
                existing_employee = existing.first()
                raise ValidationError({
                    'employee_id': f'معرف الموظف "{self.employee_id}" موجود بالفعل للموظف {existing_employee.first_name} {existing_employee.last_name}'
                })

    def save(self, *args, **kwargs):
        """
        Override save to run validation
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class EmployeeDocument(models.Model):
    """
    Separate model for additional employee documents
    """
    DOCUMENT_TYPES = [
        ('contract', 'عقد العمل'),
        ('id_card', 'بطاقة هوية'),
        ('cv', 'السيرة الذاتية'),
        ('certificate', 'شهادة'),
        ('medical_certificate', 'شهادة طبية'),
        ('photo', 'صورة شخصية'),
        ('bank_details', 'بيانات البنك'),
        ('emergency_contact', 'جهة اتصال طوارئ'),
        ('other', 'أخرى'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document = models.FileField(
        upload_to=employee_documents_path,
        storage=MediaStorage(),
        null=True, 
        blank=True
    )
    description = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.employee} - {self.get_document_type_display()}"
    
    class Meta:
        unique_together = ['employee', 'document_type']


class EmployeeHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='history')
    event = models.CharField(max_length=255)
    note = models.TextField(null=True, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.event} ({self.date})"
    

class EmployeeVirtualTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='virtual_transactions')
    date = models.DateField()
    type = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    direction = models.CharField(max_length=10, choices=[('credit', 'له'), ('debit', 'عليه')], null=True, blank=True)
    reason = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.type} - {self.amount} ({self.date})"

