import uuid
from django.db import models
from django.utils import timezone
from students.models import Student, Bus
from settings_data.models import SchoolFee, AuthorizedPayer, SchoolYear
from employees.models import Employee
from utils.services import get_next_number
from django.db import IntegrityError, transaction
from users.models import Account, CustomUser
from utils.file_handlers import payment_documents_path, payment_cheque_path
from utils.storage_backends import MediaStorage


def get_current_time():
    """Helper function to get current time only (without date)"""
    return timezone.now().time()


def get_current_date():
    """Helper function to get current date only"""
    return timezone.now().date()


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
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.display_name} ({self.type})"


class BankTransferDetail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_number = models.CharField(max_length=20, null=True, blank=True)
    branch_number = models.CharField(max_length=20, null=True, blank=True)
    account_number = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return f"{self.bank_number}-{self.branch_number}/{self.account_number}"


class ChequeDetail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_number = models.CharField(max_length=20, null=True, blank=True)
    branch_number = models.CharField(max_length=20, null=True, blank=True)
    account_number = models.CharField(max_length=30, null=True, blank=True)
    cheque_number = models.CharField(max_length=30, null=True, blank=True)
    cheque_date = models.DateField(null=True, blank=True)
    
    # ✅ Updated to use payment_cheque_path which handles ChequeDetail instances properly
    cheque_image = models.ImageField(
        upload_to=payment_cheque_path,
        storage=MediaStorage(),
        null=True, 
        blank=True,
        help_text="Cheque image or scan"
    )
    
    description = models.TextField(null=True, blank=True, help_text="Additional notes or description for the cheque")

    def __str__(self):
        return f"Cheque {self.cheque_number or self.id} ({self.cheque_date})"


class PaymentDocument(models.Model):
    """
    Separate model for additional payment-related documents
    """
    DOCUMENT_TYPES = [
        ('receipt', 'إيصال'),
        ('invoice', 'فاتورة'),
        ('contract', 'عقد'),
        ('agreement', 'اتفاقية'),
        ('bank_statement', 'كشف حساب'),
        ('transfer_receipt', 'إيصال تحويل'),
        ('other', 'أخرى'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    recipient = models.ForeignKey('Recipient', on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document = models.FileField(
        upload_to=payment_documents_path,
        storage=MediaStorage(),
        null=True, 
        blank=True
    )
    description = models.CharField(max_length=255, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        if self.payment:
            return f"Payment {self.payment.number} - {self.get_document_type_display()}"
        elif self.recipient:
            return f"Recipient {self.recipient.number} - {self.get_document_type_display()}"
        return f"Document - {self.get_document_type_display()}"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.PositiveIntegerField(unique=True, null=True, blank=True)
    receive_id = models.CharField(max_length=100, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, related_name="payments")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    authorized_payer = models.ForeignKey(AuthorizedPayer, on_delete=models.SET_NULL, null=True, blank=True)
    payment_type = models.CharField(max_length=100, null=True, blank=True)
    type = models.CharField(max_length=100, null=True, blank=True)
    cheque = models.ForeignKey('ChequeDetail', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')

    school_year = models.ForeignKey(
        'settings_data.SchoolYear',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, null=True, blank=True)

    recipient_employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    recipient_bus = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    recipient_authorized = models.ForeignKey(
        AuthorizedPayer, on_delete=models.SET_NULL, null=True, blank=True, related_name='recipient_payments'
    )

    # Separate date and time fields with proper defaults
    date = models.DateField(default=get_current_date)
    time = models.TimeField(default=get_current_time)
    
    # DateTime field for easier querying (auto-populated)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-populate date and time if not provided
        if not self.date:
            self.date = get_current_date()
        if not self.time:
            self.time = get_current_time()
            
        if self.number is None:
            for attempt in range(5):  # retry up to 5 times
                try:
                    with transaction.atomic():
                        self.number = get_next_number('payment', start=10000000)
                        super().save(*args, **kwargs)
                    break
                except IntegrityError:
                    # Retry with new number
                    continue

    def __str__(self):
        return f"Payment #{self.number} - {self.amount}"


class Recipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.PositiveIntegerField(unique=True, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, related_name="recipients")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    school_fee = models.ForeignKey(SchoolFee, on_delete=models.SET_NULL, null=True, blank=True)
    payment_type = models.CharField(max_length=100, null=True, blank=True)
    cheque = models.ForeignKey(ChequeDetail, on_delete=models.SET_NULL, null=True, blank=True, related_name="recipients")

    school_year = models.ForeignKey(
        'settings_data.SchoolYear',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recipients"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Separate date and time fields with proper defaults
    date = models.DateField(default=get_current_date)
    time = models.TimeField(default=get_current_time)
    
    # DateTime field for easier querying (auto-populated)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    received = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Auto-populate date and time if not provided
        if not self.date:
            self.date = get_current_date()
        if not self.time:
            self.time = get_current_time()
            
        if self.number is None:
            self.number = get_next_number('recipient', start=20000000)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Recipient #{self.number} - {self.amount} from {self.student}"