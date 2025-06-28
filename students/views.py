from rest_framework import generics, serializers, parsers
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from datetime import date
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import StudentDocument
from .serializers import StudentDocumentSerializer

from .models import Student, SchoolClass, StudentHistory, Bus, StudentPaymentHistory
from .serializers import (
    StudentSerializer, SchoolClassListSerializer, SchoolClassDetailSerializer,
    StudentHistorySerializer, BusSerializer, BusCreateSerializer,
    SchoolClassCreateUpdateSerializer  # Import the new serializer
)
from logs.utils import log_activity

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from payments.models import Recipient
from settings_data.models import SchoolFee, SchoolYear
from django.db.models import Sum

from decimal import Decimal
from uuid import UUID

import logging

logger = logging.getLogger(__name__)


class BusListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        return Bus.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        bus = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إنشاء باص جديد: {bus.bus_number}",
            related_model='Bus',
            related_id=str(bus.id)
        )

    def get_serializer_class(self):
        return BusCreateSerializer if self.request.method == 'POST' else BusSerializer

    def get_serializer_context(self):
        """Ensure request context is passed to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class BusRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'id'

    def get_queryset(self):
        return Bus.objects.filter(account=self.request.user.account)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BusCreateSerializer
        return BusSerializer

    def get_serializer_context(self):
        """Ensure request context is passed to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_update(self, serializer):
        bus = serializer.save()
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم تعديل بيانات الباص {bus.bus_number}",
            related_model='Bus',
            related_id=str(bus.id)
        )

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError
        
        # Check if bus has any active students
        active_students = instance.students.filter(is_archived=False).count()
        
        if active_students > 0:
            error_message = f"لا يمكن حذف الباص '{instance.name}' لأنه يحتوي على {active_students} طالب نشط. يجب نقل الطلاب إلى باص آخر أو أرشفتهم أولاً"
            
            raise ValidationError({
                'detail': error_message
            })
        
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف الباص {instance.bus_number}",
            related_model='Bus',
            related_id=str(instance.id)
        )
        
        instance.delete()

    
class BusRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    lookup_field = 'id'

    def get_queryset(self):
        return Bus.objects.filter(account=self.request.user.account)

    def get_serializer_class(self):
        # Use BusCreateSerializer for updates (PUT/PATCH) since it includes driver field
        if self.request.method in ['PUT', 'PATCH']:
            return BusCreateSerializer
        # Use BusSerializer for retrieving (GET) since it has all the computed fields
        return BusSerializer

    def perform_update(self, serializer):
        bus = serializer.save(account=self.request.user.account)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم تعديل بيانات الباص {bus.bus_number}",
            related_model='Bus',
            related_id=str(bus.id)
        )

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError
        
        # Check if bus has any active students (ignore archived students as they are considered "deleted")
        active_students = instance.students.filter(is_archived=False).count()
        
        if active_students > 0:
            error_message = f"لا يمكن حذف الباص '{instance.name}' لأنه يحتوي على {active_students} طالب نشط. يجب نقل الطلاب إلى باص آخر أو أرشفتهم أولاً"
            
            raise ValidationError({
                'detail': error_message
            })
        
        # Log the deletion before actually deleting
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف الباص {instance.bus_number}",
            related_model='Bus',
            related_id=str(instance.id)
        )
        
        # Proceed with deletion
        instance.delete()


class StudentListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_archived', 'account']
    ordering_fields = ['date_of_registration']
    permission_classes = [IsAuthenticated]
    # Add support for multipart form data (file uploads)
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        return Student.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        try:
            # First save without file if there's an attachment
            attachment = serializer.validated_data.pop('attachment', None)
            
            # Create student without attachment first
            student = serializer.save(
                account=self.request.user.account, 
                created_by=self.request.user
            )
            
            # Handle file upload separately if provided
            if attachment:
                try:
                    student.attachment = attachment
                    student.save(update_fields=['attachment'])
                except Exception as file_error:
                    # Log the file error but don't fail the student creation
                    logger.error(f"File upload failed for student {student.id}: {file_error}")
                    # You could add a message here to inform the user
                    pass
            
            # Log successful creation
            log_activity(
                user=self.request.user,
                account=self.request.user.account,
                note=f"تم إنشاء الطالب {student.first_name} {student.second_name}",
                related_model='Student',
                related_id=str(student.id)
            )
            
        except Exception as e:
            logger.error(f"Student creation error: {e}")
            raise e
            
        def get_serializer_context(self):
            """Add request context to serializer for file URL generation"""
            context = super().get_serializer_context()
            context['request'] = self.request
            return context
    
    def handle_file_upload_safely(file, student_instance):
        """
        Helper function to handle file uploads with better error handling
        """
        if not file:
            return None
        
        try:
            # Save file to student instance
            student_instance.attachment = file
            student_instance.save()
            return True
        except Exception as e:
            logger.error(f"File upload error for student {student_instance.id}: {e}")
            # Clear the file field if upload failed
            student_instance.attachment = None
            student_instance.save()
            raise Exception("File upload failed. Please check your file and try again.")


class StudentRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    # Add support for multipart form data (file uploads)
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        return Student.objects.filter(account=self.request.user.account)

    def get_serializer_context(self):
        """Add request context to serializer for file URL generation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_update(self, serializer):
        student = self.get_object()
        old_class = student.school_class
        old_bus = student.bus
        old_bus_join = student.is_bus_joined

        updated_student = serializer.save(account=self.request.user.account)

        changes = []

        if old_class != updated_student.school_class:
            StudentHistory.objects.create(
                student=updated_student,
                event="تغيير الصف",
                note=f"تم نقل الطالب من الصف '{old_class}' إلى الصف '{updated_student.school_class}'",
                date=date.today()
            )
            changes.append("الصف")

        if old_bus != updated_student.bus or old_bus_join != updated_student.is_bus_joined:
            if updated_student.is_bus_joined:
                StudentHistory.objects.create(
                    student=updated_student,
                    event="تحديث باص المدرسة",
                    note=f"تم تعيين الباص '{updated_student.bus}' للطالب",
                    date=date.today()
                )
                changes.append("الالتحاق بالباص")
            else:
                StudentHistory.objects.create(
                    student=updated_student,
                    event="إلغاء الالتحاق بالباص",
                    note="تم إزالة الطالب من الباص",
                    date=date.today()
                )
                changes.append("إزالة الباص")

        if changes:
            log_activity(
                user=self.request.user,
                account=self.request.user.account,
                note=f"تم تعديل بيانات الطالب {updated_student.first_name} {updated_student.second_name} ({'، '.join(changes)})",
                related_model='Student',
                related_id=str(updated_student.id)
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def students_with_open_accounts(request):
    """
    Returns students with unpaid fees. 
    Gracefully handles cases where no active school year exists.
    """
    account = request.user.account
    
    try:
        # Try to get the active school year
        active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
        
        if not active_year:
            # If no active year exists, return empty result instead of error
            # This allows the frontend to load without breaking
            return Response({
                "message": "لا توجد سنة دراسية مفعلة حالياً",
                "students": [],
                "has_active_year": False
            }, status=status.HTTP_200_OK)

        students = Student.objects.filter(account=account, is_archived=False)
        open_students = []

        for student in students:
            try:
                # Check if student closed account for current year
                is_closed = StudentPaymentHistory.objects.filter(
                    student=student, 
                    year=active_year.label
                ).exists()
                
                if is_closed:
                    continue  # skip closed accounts

                # Calculate total paid
                total_paid = Recipient.objects.filter(
                    student=student, 
                    school_year=active_year
                ).aggregate(Sum('amount'))['amount__sum'] or 0

                # Find the applicable fee with fallback logic
                fee = SchoolFee.objects.filter(
                    student=student, 
                    school_year=active_year
                ).first()
                
                if not fee and student.school_class:
                    fee = SchoolFee.objects.filter(
                        school_class=student.school_class, 
                        student__isnull=True, 
                        school_year=active_year
                    ).first()
                
                if not fee:
                    fee = SchoolFee.objects.filter(
                        school_class__isnull=True, 
                        student__isnull=True, 
                        school_year=active_year
                    ).first()

                # Calculate total fee with safe handling of None values
                total_fee = 0
                if fee:
                    total_fee = sum([
                        fee.school_fee or 0,
                        fee.books_fee or 0,
                        fee.trans_fee or 0,
                        fee.clothes_fee or 0,
                    ])

                # Only include students with unpaid amounts
                if total_paid < total_fee:
                    open_students.append(student)
                    
            except Exception as e:
                # Log the error but continue processing other students
                print(f"Error processing student {student.id}: {str(e)}")
                continue

        serializer = StudentSerializer(open_students, many=True, context={'request': request})
        return Response({
            "message": f"تم العثور على {len(open_students)} طالب لديهم مستحقات غير مدفوعة",
            "students": serializer.data,
            "has_active_year": True,
            "active_year": active_year.label if active_year else None
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Handle any unexpected errors gracefully
        return Response({
            "message": "حدث خطأ أثناء جلب بيانات الطلاب",
            "students": [],
            "has_active_year": False,
            "error": str(e) if hasattr(request.user, 'is_superuser') and request.user.is_superuser else None
        }, status=status.HTTP_200_OK)


class SchoolClassListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SchoolClass.objects.filter(account=self.request.user.account)

    def get_serializer_class(self):
        """Use different serializers for different operations"""
        if self.request.method == 'POST':
            return SchoolClassCreateUpdateSerializer  # For creating
        return SchoolClassListSerializer  # For listing

    def perform_create(self, serializer):
        class_obj = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إنشاء الصف {class_obj.name}",
            related_model='SchoolClass',
            related_id=str(class_obj.id)
        )


class SchoolClassRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return SchoolClass.objects.filter(account=self.request.user.account)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SchoolClassCreateUpdateSerializer
        return SchoolClassDetailSerializer

    def get_serializer_context(self):
        """Ensure request context is passed to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_update(self, serializer):
        class_obj = serializer.save()
        
        # Log activity after successful save
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم تعديل الصف {class_obj.name}",
            related_model='SchoolClass',
            related_id=str(class_obj.id)
        )

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError
        
        # Check if class has any active students
        active_students = instance.students.filter(is_archived=False).count()
        
        if active_students > 0:
            error_message = f"لا يمكن حذف الصف '{instance.name}' لأنه يحتوي على {active_students} طالب نشط. يجب نقل الطلاب إلى صف آخر أو أرشفتهم أولاً"
            
            raise ValidationError({
                'detail': error_message
            })
        
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف الصف {instance.name}",
            related_model='SchoolClass',
            related_id=str(instance.id)
        )
        
        instance.delete()


class StudentHistoryListCreateView(generics.ListCreateAPIView):
    serializer_class = StudentHistorySerializer

    def get_queryset(self):
        return StudentHistory.objects.filter(student__account=self.request.user.account)


class StudentHistoryDetailView(generics.RetrieveAPIView):
    queryset = StudentHistory.objects.all()
    serializer_class = StudentHistorySerializer
    lookup_field = 'id'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_student_account(request, id):
    """
    Closes a student account for a specific year.
    Improved with better error handling.
    """
    try:
        student = Student.objects.get(id=id, account=request.user.account)
        year_label = request.data.get("year")
        
        if not year_label:
            return Response({
                "error": "يجب تحديد السنة الدراسية"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get or create the school year
        school_year, created = SchoolYear.objects.get_or_create(
            label=year_label,
            account=request.user.account,
            defaults={'created_by': request.user}
        )

        # Check if account is already closed
        if StudentPaymentHistory.objects.filter(student=student, year=year_label).exists():
            return Response({
                "error": "حساب الطالب مغلق بالفعل لهذه السنة"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update all current payments to link them with this year
        payments_qs = Recipient.objects.filter(student=student, school_year__isnull=True)
        updated_count = payments_qs.update(school_year=school_year)

        # Get serialized copy of payments
        payments = list(payments_qs.values())

        for p in payments:
            for k, v in p.items():
                if isinstance(v, UUID):
                    p[k] = str(v)
                elif isinstance(v, Decimal):
                    p[k] = float(v)

        # Get student-level school fee
        fee = SchoolFee.objects.filter(student=student).first()
        fee_data = None
        if fee:
            fee_data = {
                "school_fee": fee.school_fee,
                "books_fee": fee.books_fee,
                "trans_fee": fee.trans_fee,
                "clothes_fee": fee.clothes_fee,
            }
            fee.delete()

        total_paid = payments_qs.aggregate(Sum("amount"))["amount__sum"] or 0

        # Save to payment history
        StudentPaymentHistory.objects.create(
            student=student,
            year=year_label,
            total_paid=total_paid,
            fees_snapshot=fee_data,
            payments_snapshot=payments,
            created_by=request.user
        )

        # Log the activity
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم إغلاق حساب الطالب {student.first_name} {student.second_name} للسنة {year_label}",
            related_model='Student',
            related_id=str(student.id)
        )

        return Response({
            "message": "تم تسكير الحساب بنجاح",
            "total_paid": float(total_paid),
            "payments_updated": updated_count,
            "year": year_label
        }, status=status.HTTP_200_OK)
        
    except Student.DoesNotExist:
        return Response({
            "error": "الطالب غير موجود"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "error": "حدث خطأ أثناء إغلاق الحساب",
            "details": str(e) if hasattr(request.user, 'is_superuser') and request.user.is_superuser else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_student_document(request, student_id):
    """Upload a document for a specific student"""
    try:
        student = Student.objects.get(id=student_id, account=request.user.account)
        
        document_type = request.data.get('document_type')
        document_file = request.FILES.get('document')
        description = request.data.get('description', '')
        
        if not document_type or not document_file:
            return Response({
                'error': 'نوع الوثيقة والملف مطلوبان'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if document type already exists for this student
        existing_doc = StudentDocument.objects.filter(
            student=student, 
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
            document = StudentDocument.objects.create(
                student=student,
                document_type=document_type,
                document=document_file,
                description=description,
                uploaded_by=request.user
            )
        
        serializer = StudentDocumentSerializer(document, context={'request': request})
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم رفع وثيقة {document.get_document_type_display()} للطالب {student.first_name} {student.second_name}",
            related_model='StudentDocument',
            related_id=str(document.id)
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Student.DoesNotExist:
        return Response({
            'error': 'الطالب غير موجود'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء رفع الوثيقة',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_student_document(request, document_id):
    """Delete a student document"""
    try:
        document = StudentDocument.objects.get(
            id=document_id, 
            student__account=request.user.account
        )
        
        # Delete from S3
        if document.document:
            s3_manager = S3FileManager()
            s3_manager.delete_file(document.document.name)
        
        student_name = f"{document.student.first_name} {document.student.second_name}"
        doc_type = document.get_document_type_display()
        
        document.delete()
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم حذف وثيقة {doc_type} للطالب {student_name}",
            related_model='StudentDocument',
            related_id=str(document.id)
        )
        
        return Response({
            'message': 'تم حذف الوثيقة بنجاح'
        }, status=status.HTTP_200_OK)
        
    except StudentDocument.DoesNotExist:
        return Response({
            'error': 'الوثيقة غير موجودة'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'حدث خطأ أثناء حذف الوثيقة'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)