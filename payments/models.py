import uuid
from django.db import models
from students.models import Student, Bus
from settings_data.models import SchoolFee
from settings_data.models import AuthorizedPayer
from employees.models import Employee

class PaymentType(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=50, unique=True, null=True, blank=True)
    display_name = models.CharField(max_length=100, null=True, blank=True)
    
    type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"{self.display_name} ({self.type})"


class BankTransferDetail(models.Model):
    """
    Details for a bank‐transfer payment.
    Linked later to a Payment record.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_number = models.CharField(max_length=20, null=True, blank=True)
    branch_number = models.CharField(max_length=20, null=True, blank=True)
    account_number = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return f"{self.bank_number}-{self.branch_number}/{self.account_number}"


class ChequeDetail(models.Model):
    """
    Details for a cheque payment.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_number = models.CharField(max_length=20, null=True, blank=True)
    branch_number = models.CharField(max_length=20, null=True, blank=True)
    account_number = models.CharField(max_length=30, null=True, blank=True)
    cheque_date = models.DateField(null=True, blank=True)
    cheque_image = models.ImageField(upload_to='cheques/', null=True, blank=True)

    def __str__(self):
        return f"Cheque {self.id} ({self.cheque_date})"
    

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receive_id = models.CharField(max_length=100, null=True, blank=True)
    
    authorized_payer = models.ForeignKey(AuthorizedPayer, on_delete=models.SET_NULL, null=True, blank=True)
    payment_type = models.ForeignKey(PaymentType, on_delete=models.SET_NULL, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, null=True, blank=True)

    recipient_employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    recipient_bus = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True, blank=True)
    recipient_authorized = models.ForeignKey(AuthorizedPayer, on_delete=models.SET_NULL, null=True, blank=True, related_name='recipient_payments')

    date = models.DateField()

    def __str__(self):
        return f"Payment {self.id} - {self.amount}"


class Recipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    school_fee = models.ForeignKey(SchoolFee, on_delete=models.SET_NULL, null=True, blank=True)
    payment_type = models.ForeignKey(PaymentType, on_delete=models.SET_NULL, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    def __str__(self):
        return f"Recipient {self.id} - {self.amount} from {self.student}"
