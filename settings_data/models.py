from django.db import models
import uuid
from django.db.models import Q
from users.models import Account, CustomUser  # ✅ assuming you have these models

class EmployeeType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    display_value = models.CharField(max_length=100)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='employee_types', null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    is_teacher = models.BooleanField(default=False, null=True, blank=True)
    is_driver = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return self.display_value


class AuthorizedPayer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    display_value = models.CharField(max_length=100)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='authorized_payers', null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.display_value
    
class SchoolYear(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=20)  # e.g., "23/24"
    is_active = models.BooleanField(default=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="school_years")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label


class SchoolFee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_class = models.ForeignKey('students.SchoolClass', on_delete=models.SET_NULL, null=True, blank=True)
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True)

    school_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    books_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    trans_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    clothes_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    year = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='school_fees', null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        if self.student:
            return f"Fees for {self.student}"
        elif self.school_class:
            return f"Fees for class {self.school_class}"
        return "Default School Fees"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school_class', 'student', 'account'],
                name='unique_fee_per_student_or_class_per_account',
                condition=Q(school_class__isnull=True, student__isnull=True)  # Only one default per account
            )
        ]
