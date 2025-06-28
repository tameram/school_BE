from rest_framework import generics, viewsets, parsers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend

from .models import Employee, EmployeeHistory, EmployeeVirtualTransaction, EmployeeDocument
from .serializers import (
    EmployeeSerializer, 
    EmployeeHistorySerializer, 
    EmployeeVirtualTransactionSerializer,
    EmployeeDocumentSerializer
)
from logs.utils import log_activity
from utils.s3_utils import S3FileManager
from payments.models import Payment
from payments.serializers import PaymentSerializer

import logging
logger = logging.getLogger(__name__)


class EmployeeListCreateView(generics.ListCreateAPIView):
    serializer_class = EmployeeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee_type', 'is_archived']
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        return Employee.objects.filter(account=self.request.user.account)

    def get_serializer_context(self):
        """Add request context to serializer for file URL generation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        try:
            # Handle file uploads separately if needed
            contract_pdf = serializer.validated_data.pop('contract_pdf', None)
            profile_picture = serializer.validated_data.pop('profile_picture', None)
            id_copy = serializer.validated_data.pop('id_copy', None)
            
            # Create employee
            instance = serializer.save(
                account=self.request.user.account, 
                created_by=self.request.user
            )
            
            # Handle file uploads
            files_to_upload = [
                (contract_pdf, 'contract_pdf'),
                (profile_picture, 'profile_picture'),
                (id_copy, 'id_copy')
            ]
            
            for file_obj, field_name in files_to_upload:
                if file_obj:
                    try:
                        setattr(instance, field_name, file_obj)
                        instance.save(update_fields=[field_name])
                    except Exception as file_error:
                        logger.error(f"File upload failed for employee {instance.id}, field {field_name}: {file_error}")
            
            log_activity(
                user=self.request.user,
                account=self.request.user.account,
                note=f"تم إنشاء الموظف {instance.first_name} {instance.last_name}",
                related_model='Employee',
                related_id=str(instance.id)
            )
            
        except Exception as e:
            logger.error(f"Employee creation error: {e}")
            raise e


class EmployeePaymentCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def post(self, request, employee_id):
        try:
            employee = Employee.objects.get(id=employee_id, account=request.user.account)
        except Employee.DoesNotExist:
            return Response({'detail': 'الموظف غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['recipient_employee'] = str(employee.id)
        data['account'] = str(request.user.account.id)
        data['created_by'] = str(request.user.id)

        serializer = PaymentSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    lookup_field = 'id'

    def get_queryset(self):
        return Employee.objects.filter(account=self.request.user.account)

    def get_serializer_context(self):
        """Add request context to serializer for file URL generation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_update(self, serializer):
        instance = serializer.save(account=self.request.user.account)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم تعديل بيانات الموظف {instance.first_name} {instance.last_name}",
            related_model='Employee',
            related_id=str(instance.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف الموظف {instance.first_name} {instance.last_name}",
            related_model='Employee',
            related_id=str(instance.id)
        )
        instance.delete()


class EmployeeHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeHistorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmployeeHistory.objects.filter(employee__account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إضافة سجل للموظف {instance.employee.first_name} {instance.employee.last_name} - {instance.event}",
            related_model='EmployeeHistory',
            related_id=str(instance.id)
        )


class EmployeeVirtualTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeVirtualTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'date']

    def get_queryset(self):
        return EmployeeVirtualTransaction.objects.filter(account=self.request.user.account).order_by('-date')

    def perform_create(self, serializer):
        serializer.save(
            account=self.request.user.account,
            created_by=self.request.user
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_employee_document(request, employee_id):
    """Upload a document for a specific employee"""
    try:
        employee = Employee.objects.get(id=employee_id, account=request.user.account)
        
        document_type = request.data.get('document_type')
        document_file = request.FILES.get('document')
        description = request.data.get('description', '')
        
        if not document_type or not document_file:
            return Response({
                'error': 'نوع الوثيقة والملف مطلوبان'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if document type already exists for this employee
        existing_doc = EmployeeDocument.objects.filter(
            employee=employee, 
            document_type=document_type
        ).first()
        
        if existing_doc:
            # Update existing document
            existing_doc.document = document_file
            existing_doc.description = description
            existing_doc.uploaded_by = request.user
            existing_doc.save()
            document = existing_doc
        else:
            # Create new document
            document = EmployeeDocument.objects.create(
                employee=employee,
                document_type=document_type,
                document=document_file,
                description=description,
                uploaded_by=request.user
            )
        
        serializer = EmployeeDocumentSerializer(document, context={'request': request})
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم رفع وثيقة {document.get_document_type_display()} للموظف {employee.first_name} {employee.last_name}",
            related_model='EmployeeDocument',
            related_id=str(document.id)
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Employee.DoesNotExist:
        return Response({
            'error': 'الموظف غير موجود'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء رفع الوثيقة',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_employee_document(request, document_id):
    """Delete an employee document"""
    try:
        document = EmployeeDocument.objects.get(
            id=document_id, 
            employee__account=request.user.account
        )
        
        # Delete from S3
        if document.document:
            s3_manager = S3FileManager()
            s3_manager.delete_file(document.document.name)
        
        employee_name = f"{document.employee.first_name} {document.employee.last_name}"
        doc_type = document.get_document_type_display()
        
        document.delete()
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم حذف وثيقة {doc_type} للموظف {employee_name}",
            related_model='EmployeeDocument',
            related_id=str(document.id)
        )
        
        return Response({
            'message': 'تم حذف الوثيقة بنجاح'
        }, status=status.HTTP_200_OK)
        
    except EmployeeDocument.DoesNotExist:
        return Response({
            'error': 'الوثيقة غير موجودة'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء حذف الوثيقة'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_dashboard_stats(request):
    """Get dashboard statistics for employees"""
    account = request.user.account
    
    try:
        employees_qs = Employee.objects.filter(account=account)
        
        # Basic counts
        total_employees = employees_qs.count()
        active_employees = employees_qs.filter(is_archived=False).count()
        archived_employees = employees_qs.filter(is_archived=True).count()
        
        # Employee type breakdown
        type_stats = employees_qs.filter(is_archived=False).values(
            'employee_type__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Salary statistics
        salary_stats = employees_qs.filter(
            is_archived=False,
            base_salary__isnull=False
        ).aggregate(
            total_salaries=Sum('base_salary'),
            avg_salary=Avg('base_salary'),
            min_salary=Min('base_salary'),
            max_salary=Max('base_salary')
        )
        
        return Response({
            'total_employees': total_employees,
            'active_employees': active_employees,
            'archived_employees': archived_employees,
            'type_breakdown': list(type_stats),
            'salary_stats': salary_stats
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء جلب إحصائيات الموظفين',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

