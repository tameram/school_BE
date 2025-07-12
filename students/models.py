from django.db import models
import uuid
from users.models import Account, CustomUser
from utils.file_handlers import student_documents_path
from utils.storage_backends import MediaStorage




class SchoolClass(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='classes', null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    teacher = models.ForeignKey('employees.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name="classes")

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ['name', 'account']


class Bus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, null=True, blank=True)
    bus_number = models.CharField(max_length=50, null=True, blank=True)
    bus_type = models.CharField(max_length=100, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='buses', null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    manager_name = models.CharField(max_length=100, null=True, blank=True)
    driver = models.ForeignKey('employees.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name="buses")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.bus_number})"
    
    class Meta:
        unique_together = [
            ['name', 'account'],
            ['bus_number', 'account']
        ]


class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey('users.Account', on_delete=models.CASCADE, related_name='students', null=True, blank=True)

    student_id = models.CharField(max_length=50, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    second_name = models.CharField(max_length=100, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    school_class = models.ForeignKey('students.SchoolClass', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    date_of_registration = models.DateField(null=True, blank=True)
    is_archived = models.BooleanField(default=False, blank=True)

    is_bus_joined = models.BooleanField(null=True, blank=True)
    bus = models.ForeignKey('students.Bus', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')

    parent_name = models.CharField(max_length=255, null=True, blank=True)
    parent_phone = models.CharField(max_length=20, null=True, blank=True)
    parent_phone_2 = models.CharField(max_length=20, null=True, blank=True)  # New optional phone field
    parent_email = models.EmailField(null=True, blank=True)

    address = models.TextField(null=True, blank=True, help_text="عنوان")

    note = models.TextField(null=True, blank=True)
    
    # File upload field for documents/images
    attachment = models.FileField(
        upload_to=student_documents_path,
        storage=MediaStorage(),  # ✅ This is the key change
        null=True,
        blank=True,
        help_text="Student profile document (ID, photo, etc.)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.second_name or ''}".strip()

class StudentDocument(models.Model):
    DOCUMENT_TYPES = [
        ('id_card', 'بطاقة هوية'),
        ('birth_certificate', 'شهادة ميلاد'),
        ('medical_record', 'سجل طبي'),
        ('photo', 'صورة شخصية'),
        ('previous_grades', 'درجات سابقة'),
        ('transfer_certificate', 'شهادة نقل'),
        ('parent_id', 'هوية ولي الأمر'),
        ('other', 'أخرى'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document = models.FileField(upload_to='student_documents/', null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.student} - {self.get_document_type_display()}"
    
    class Meta:
        unique_together = ['student', 'document_type'] 


class StudentHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='history')
    event = models.CharField(max_length=255, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.event}"


class StudentPaymentHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='payment_history')
    year = models.CharField(max_length=20)  # e.g., "20/21"
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fees_snapshot = models.JSONField(null=True, blank=True)
    payments_snapshot = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.year}"