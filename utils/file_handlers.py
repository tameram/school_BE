import os
from django.utils.deconstruct import deconstructible


@deconstructible
class CustomUploadPath:
    def __init__(self, sub_path):
        self.sub_path = sub_path

    def __call__(self, instance, filename):
        # Get account name safely
        if hasattr(instance, 'account') and instance.account:
            account_name = instance.account.name or str(instance.account.id)
        else:
            account_name = 'default'
        
        # Clean account name for file path
        account_name = "".join(c for c in account_name if c.isalnum() or c in (' ', '-', '_')).strip()
        account_name = account_name.replace(' ', '_') or 'default'
        
        # Determine user type and ID based on instance
        if hasattr(instance, 'student') and instance.student:
            user_id = str(instance.student.id)
            user_type = 'student'
        elif hasattr(instance, 'employee') and instance.employee:
            user_id = str(instance.employee.id)
            user_type = 'employee'
        elif hasattr(instance, 'id') and str(type(instance).__name__).lower() == 'student':
            # For direct student uploads
            user_id = str(instance.id)
            user_type = 'student'
        else:
            user_id = 'unknown'
            user_type = 'general'
        
        # Clean filename
        name, ext = os.path.splitext(filename)
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_') or 'file'
        safe_filename = f"{safe_name}{ext}"
        
        # Create path: account_name/category/user_type/user_id/filename
        return f"{account_name}/{self.sub_path}/{user_type}/{user_id}/{safe_filename}"
    
student_documents_path = CustomUploadPath('students')
payment_documents_path = CustomUploadPath('payments')
receipt_documents_path = CustomUploadPath('receipts')
employee_documents_path = CustomUploadPath('employees')
general_documents_path = CustomUploadPath('general')