
from utils.s3_utils import S3FileManager
from employees.models import Employee, EmployeeDocument
from students.models import Student, StudentDocument
from django.core.management.base import BaseCommand
import logging

logger = logging.getLogger(__name__)


class FileCleanupManager:
    """
    Utility class for managing file cleanup operations
    """
    
    def __init__(self):
        self.s3_manager = S3FileManager()
    
    def cleanup_orphaned_employee_files(self):
        """
        Clean up S3 files that are no longer referenced by any employee records
        """
        if not self.s3_manager.is_available():
            logger.warning("S3 manager not available for cleanup")
            return
        
        try:
            # Get all employee files from S3
            employee_files = self.s3_manager.list_files('media/employees/')
            
            # Get all file references from database
            db_files = set()
            
            # Employee main files
            for employee in Employee.objects.all():
                if employee.contract_pdf:
                    db_files.add(employee.contract_pdf.name)
                if employee.profile_picture:
                    db_files.add(employee.profile_picture.name)
                if employee.id_copy:
                    db_files.add(employee.id_copy.name)
            
            # Employee document files
            for doc in EmployeeDocument.objects.all():
                if doc.document:
                    db_files.add(doc.document.name)
            
            # Find orphaned files
            orphaned_files = []
            for s3_file in employee_files:
                file_key = s3_file.get('Key', '')
                # Remove 'media/' prefix for comparison
                file_name = file_key.replace('media/', '', 1) if file_key.startswith('media/') else file_key
                
                if file_name not in db_files:
                    orphaned_files.append(file_key)
            
            # Delete orphaned files
            deleted_count = 0
            for orphaned_file in orphaned_files:
                if self.s3_manager.delete_file(orphaned_file):
                    deleted_count += 1
                    logger.info(f"Deleted orphaned file: {orphaned_file}")
            
            logger.info(f"Cleanup completed. Deleted {deleted_count} orphaned employee files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during employee file cleanup: {e}")
            return 0
    
    def cleanup_orphaned_student_files(self):
        """
        Clean up S3 files that are no longer referenced by any student records
        """
        if not self.s3_manager.is_available():
            logger.warning("S3 manager not available for cleanup")
            return
        
        try:
            # Get all student files from S3
            student_files = self.s3_manager.list_files('media/students/')
            
            # Get all file references from database
            db_files = set()
            
            # Student main files
            for student in Student.objects.all():
                if student.attachment:
                    db_files.add(student.attachment.name)
            
            # Student document files
            for doc in StudentDocument.objects.all():
                if doc.document:
                    db_files.add(doc.document.name)
            
            # Find orphaned files
            orphaned_files = []
            for s3_file in student_files:
                file_key = s3_file.get('Key', '')
                file_name = file_key.replace('media/', '', 1) if file_key.startswith('media/') else file_key
                
                if file_name not in db_files:
                    orphaned_files.append(file_key)
            
            # Delete orphaned files
            deleted_count = 0
            for orphaned_file in orphaned_files:
                if self.s3_manager.delete_file(orphaned_file):
                    deleted_count += 1
                    logger.info(f"Deleted orphaned file: {orphaned_file}")
            
            logger.info(f"Cleanup completed. Deleted {deleted_count} orphaned student files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during student file cleanup: {e}")
            return 0

