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
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.label


class SchoolFee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_class = models.ForeignKey('students.SchoolClass', on_delete=models.SET_NULL, null=True, blank=True)
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True)

    school_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    books_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    trans_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    clothes_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    
    # New discount fields
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        default=0,
        help_text="Discount percentage (0-100)"
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        default=0,
        help_text="Fixed discount amount"
    )

    clothes_fee_paid = models.BooleanField(default=False, null=True, blank=True)

    school_year = models.ForeignKey(
        'settings_data.SchoolYear',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="school_fees"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    year = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='school_fees', null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def get_total_fees_before_discount(self):
        """Calculate total fees before applying discount"""
        return (
            (self.school_fee or 0) + 
            (self.books_fee or 0) + 
            (self.trans_fee or 0) + 
            (self.clothes_fee or 0)
        )

    def get_discount_amount_calculated(self):
        """Calculate the actual discount amount based on percentage and fixed amount"""
        total_before_discount = self.get_total_fees_before_discount()
        
        # Calculate percentage discount
        percentage_discount = 0
        if self.discount_percentage:
            percentage_discount = (total_before_discount * self.discount_percentage) / 100
        
        # Add fixed amount discount
        fixed_discount = self.discount_amount or 0
        
        return percentage_discount + fixed_discount

    def get_total_fees_after_discount(self):
        """Calculate total fees after applying discount"""
        total_before_discount = self.get_total_fees_before_discount()
        discount_amount = self.get_discount_amount_calculated()
        
        final_total = total_before_discount - discount_amount
        
        # Ensure the final total is not negative
        return max(final_total, 0)

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
        