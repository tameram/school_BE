import os
from django.utils.deconstruct import deconstructible


def clean_name(name):
    """Clean name for use in file paths"""
    if not name:
        return 'unknown'
    clean = "".join(c for c in str(name) if c.isalnum() or c in (' ', '-', '_')).strip()
    return clean.replace(' ', '_') or 'unknown'


def get_account_name(instance):
    """Get account name from instance"""
    if hasattr(instance, 'account') and instance.account:
        return clean_name(instance.account.name or str(instance.account.id))
    return 'default'


@deconstructible
class StudentDocumentPath:
    """Path: media/{account_name}/students/{student_id}/"""
    
    def __call__(self, instance, filename):
        account_name = get_account_name(instance)
        
        # For StudentDocument model
        if hasattr(instance, 'student') and instance.student:
            student_id = clean_name(instance.student.student_id or instance.student.id)
        # For Student model direct upload
        else:
            student_id = clean_name(instance.student_id or instance.id)
        
        safe_filename = clean_name(os.path.splitext(filename)[0]) + os.path.splitext(filename)[1]
        return f"{account_name}/students/{student_id}/{safe_filename}"


@deconstructible
class EmployeeDocumentPath:
    """Path: media/{account_name}/employees/{employee_id}/"""
    
    def __call__(self, instance, filename):
        account_name = get_account_name(instance)
        
        # For EmployeeDocument model
        if hasattr(instance, 'employee') and instance.employee:
            employee_id = clean_name(instance.employee.employee_id or instance.employee.id)
        # For Employee model direct upload
        else:
            employee_id = clean_name(instance.employee_id or instance.id)
        
        safe_filename = clean_name(os.path.splitext(filename)[0]) + os.path.splitext(filename)[1]
        return f"{account_name}/employees/{employee_id}/{safe_filename}"


@deconstructible
class RecipientChequePath:
    """Path: media/{account_name}/students/{student_id}/recipient/"""
    
    def __call__(self, instance, filename):
        account_name = get_account_name(instance)
        student_id = clean_name(instance.student.student_id or instance.student.id)
        
        # Use recipient number as filename
        recipient_number = instance.number or 'unknown'
        ext = os.path.splitext(filename)[1]
        safe_filename = f"{recipient_number}{ext}"
        
        return f"{account_name}/students/{student_id}/recipient/{safe_filename}"


@deconstructible
class PaymentChequePath:
    """Dynamic path based on payment recipient type"""
    
    def __call__(self, instance, filename):
        # For ChequeDetail instances, we need to get account from related objects
        if hasattr(instance, 'payments') and instance.payments.exists():
            # Get the first payment using this cheque
            payment = instance.payments.first()
            account_name = get_account_name(payment)
        elif hasattr(instance, 'recipients') and instance.recipients.exists():
            # Get the first recipient using this cheque
            recipient = instance.recipients.first()
            account_name = get_account_name(recipient)
            student_id = clean_name(recipient.student.student_id or recipient.student.id)
            recipient_number = recipient.number or 'unknown'
            ext = os.path.splitext(filename)[1]
            safe_filename = f"{recipient_number}{ext}"
            return f"{account_name}/students/{student_id}/recipient/{safe_filename}"
        else:
            # Fallback for direct cheque upload - try to get account from instance
            if hasattr(instance, 'account'):
                account_name = get_account_name(instance)
            else:
                account_name = 'default'
            payment_number = getattr(instance, 'cheque_number', getattr(instance, 'id', 'unknown'))
            ext = os.path.splitext(filename)[1]
            safe_filename = f"{payment_number}{ext}"
            return f"{account_name}/generalPayments/{safe_filename}"
        
        # Handle payment-based routing
        payment = instance.payments.first() if hasattr(instance, 'payments') and instance.payments.exists() else None
        if not payment:
            # Fallback
            account_name = get_account_name(instance) if hasattr(instance, 'account') else 'default'
            payment_number = getattr(instance, 'cheque_number', getattr(instance, 'id', 'unknown'))
            ext = os.path.splitext(filename)[1]
            safe_filename = f"{payment_number}{ext}"
            return f"{account_name}/generalPayments/{safe_filename}"
        
        payment_number = payment.number or 'unknown'
        ext = os.path.splitext(filename)[1]
        safe_filename = f"{payment_number}{ext}"
        
        # Determine path based on recipient type
        if payment.recipient_employee:
            employee_id = clean_name(payment.recipient_employee.employee_id or payment.recipient_employee.id)
            return f"{account_name}/employees/{employee_id}/Payment/{safe_filename}"
        
        elif payment.recipient_bus:
            bus_number = clean_name(payment.recipient_bus.bus_number or payment.recipient_bus.id)
            return f"{account_name}/buses/{bus_number}/Payment/{safe_filename}"
        
        elif payment.recipient_authorized:
            authorized_name = clean_name(payment.recipient_authorized.name or payment.recipient_authorized.id)
            return f"{account_name}/authorized/{authorized_name}/Payment/{safe_filename}"
        
        else:
            return f"{account_name}/generalPayments/{safe_filename}"


@deconstructible
class PaymentDocumentPath:
    """Path for PaymentDocument model based on related payment or recipient"""
    
    def __call__(self, instance, filename):
        account_name = get_account_name(instance)
        safe_filename = clean_name(os.path.splitext(filename)[0]) + os.path.splitext(filename)[1]
        
        if instance.payment:
            # Use payment's logic for path determination
            payment = instance.payment
            
            if payment.recipient_employee:
                employee_id = clean_name(payment.recipient_employee.employee_id or payment.recipient_employee.id)
                return f"{account_name}/employees/{employee_id}/Payment/{safe_filename}"
            
            elif payment.recipient_bus:
                bus_number = clean_name(payment.recipient_bus.bus_number or payment.recipient_bus.id)
                return f"{account_name}/buses/{bus_number}/Payment/{safe_filename}"
            
            elif payment.recipient_authorized:
                authorized_name = clean_name(payment.recipient_authorized.name or payment.recipient_authorized.id)
                return f"{account_name}/authorized/{authorized_name}/Payment/{safe_filename}"
            
            else:
                return f"{account_name}/generalPayments/{safe_filename}"
        
        elif instance.recipient:
            # For recipient documents
            student_id = clean_name(instance.recipient.student.student_id or instance.recipient.student.id)
            return f"{account_name}/students/{student_id}/recipient/{safe_filename}"
        
        else:
            return f"{account_name}/generalPayments/{safe_filename}"


@deconstructible
class LogoPath:
    """Path: media/{account_name}/"""
    
    def __call__(self, instance, filename):
        account_name = get_account_name(instance)
        safe_filename = clean_name(os.path.splitext(filename)[0]) + os.path.splitext(filename)[1]
        return f"{account_name}/{safe_filename}"


# Create instances for use in models
student_documents_path = StudentDocumentPath()
employee_documents_path = EmployeeDocumentPath()
recipient_cheque_path = RecipientChequePath()
payment_cheque_path = PaymentChequePath()
payment_documents_path = PaymentDocumentPath()
logo_path = LogoPath()

# Legacy compatibility - keep these for existing imports
receipt_documents_path = PaymentDocumentPath()
general_documents_path = LogoPath()