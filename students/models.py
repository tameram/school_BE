from django.db import models
import uuid
from accounts.models import Account


class SchoolClass(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, null=True, blank=True)
    # teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # future

    def __str__(self):
        return self.name
    

class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='students', null=True, blank=True)

    student_id = models.CharField(max_length=50, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    second_name = models.CharField(max_length=100, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)  # e.g., 'Male', 'Female', etc.
    birthdate = models.DateField(null=True, blank=True)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    date_of_registration = models.DateField(null=True, blank=True)
    is_archived = models.BooleanField(default=False, null=True, blank=True)

    is_bus_joined = models.BooleanField(null=True, blank=True)
    bus = models.CharField(max_length=100, null=True, blank=True)  # Will be ForeignKey later

    parent_name = models.CharField(max_length=255, null=True, blank=True)
    parent_phone = models.CharField(max_length=20, null=True, blank=True)
    parent_email = models.EmailField(null=True, blank=True)

    note = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.second_name or ''}".strip()

class StudentHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='history')
    event = models.CharField(max_length=255)
    note = models.TextField(null=True, blank=True)
    date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.event}"


