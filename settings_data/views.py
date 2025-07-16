from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from students.models import Student
from .models import EmployeeType, AuthorizedPayer, SchoolFee, SchoolYear
from .serializers import EmployeeTypeSerializer, AuthorizedPayerSerializer, SchoolFeeSerializer, SchoolYearSerializer
from logs.utils import log_activity
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Case, When, Value
from django.db.models.functions import Greatest


class EmployeeTypeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeType.objects.all()
    serializer_class = EmployeeTypeSerializer

    def get_queryset(self):
        return EmployeeType.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إضافة نوع موظف: {instance.name}",
            related_model='EmployeeType',
            related_id=str(instance.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف نوع الموظف: {instance.name}",
            related_model='EmployeeType',
            related_id=str(instance.id)
        )
        instance.delete()


class AuthorizedPayerViewSet(viewsets.ModelViewSet):
    queryset = AuthorizedPayer.objects.all()
    serializer_class = AuthorizedPayerSerializer

    def get_queryset(self):
        return AuthorizedPayer.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم إضافة دافع معتمد: {instance.name}",
            related_model='AuthorizedPayer',
            related_id=str(instance.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note=f"تم حذف الدافع المعتمد: {instance.name}",
            related_model='AuthorizedPayer',
            related_id=str(instance.id)
        )
        instance.delete()

class SchoolYearViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolYearSerializer
    permission_classes = [IsAuthenticated]
    queryset = SchoolYear.objects.all()
    
    def get_queryset(self):
        return SchoolYear.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        # 1. Create the new school year
        school_year = serializer.save(account=self.request.user.account, created_by=self.request.user)

        # 2. Get the default school fee
        default_fee = SchoolFee.objects.filter(
            account=self.request.user.account,
            school_class__isnull=True,
            student__isnull=True
        ).first()

        if not default_fee:
            return  # No default to apply

        # 3. Get all non-archived students
        students = Student.objects.filter(account=self.request.user.account, is_archived=False)

        # 4. Bulk create school fee records for those students
        fees_to_create = []
        for student in students:
            fees_to_create.append(SchoolFee(
                student=student,
                school_year=school_year,
                school_fee=default_fee.school_fee or 0,
                books_fee=default_fee.books_fee or 0,
                trans_fee=default_fee.trans_fee or 0,
                clothes_fee=default_fee.clothes_fee or 0,
                clothes_fee_paid=default_fee.clothes_fee_paid or False,
                discount_percentage=default_fee.discount_percentage or 0,
                discount_amount=default_fee.discount_amount or 0,
                account=self.request.user.account,
                created_by=self.request.user
            ))

        SchoolFee.objects.bulk_create(fees_to_create)

    @action(detail=False, methods=['patch'], url_path='deactivate')
    def deactivate_all(self, request):
        SchoolYear.objects.filter(account=request.user.account, is_active=True).update(is_active=False)
        return Response({"detail": "Deactivated previous active years"})


class SchoolFeeViewSet(viewsets.ModelViewSet):
    queryset = SchoolFee.objects.all()
    serializer_class = SchoolFeeSerializer

    def get_queryset(self):
        return SchoolFee.objects.filter(account=self.request.user.account)

    def perform_create(self, serializer):
        instance = serializer.save(account=self.request.user.account, created_by=self.request.user)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note="تم إنشاء رسوم مدرسية",
            related_model='SchoolFee',
            related_id=str(instance.id)
        )

    def perform_update(self, serializer):
        instance = serializer.save(account=self.request.user.account)
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note="تم تعديل رسوم مدرسية",
            related_model='SchoolFee',
            related_id=str(instance.id)
        )

    def perform_destroy(self, instance):
        log_activity(
            user=self.request.user,
            account=self.request.user.account,
            note="تم حذف رسوم مدرسية",
            related_model='SchoolFee',
            related_id=str(instance.id)
        )
        instance.delete()

    @action(detail=False, methods=['post', 'put'], url_path='update-by-student')
    def update_by_student(self, request):
        """Update or create school fee for a specific student"""
        print(f"🔥 Received request data: {request.data}")
        
        student_id = request.data.get('student')
        school_year_id = request.data.get('school_year')
        
        print(f"📝 Student ID: {student_id}, School Year ID: {school_year_id}")
        
        if not student_id or not school_year_id:
            return Response(
                {"error": "student and school_year are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Try to get existing school fee
            print(f"🔍 Looking for existing fee with student={student_id}, school_year={school_year_id}, account={request.user.account.id}")
            
            school_fee = SchoolFee.objects.get(
                account=request.user.account,
                student_id=student_id,
                school_year_id=school_year_id
            )
            print(f"✅ Found existing fee: {school_fee.id}")
            
            # Update existing
            serializer = self.get_serializer(school_fee, data=request.data, partial=True)
            action_type = "تم تعديل"
            
        except SchoolFee.DoesNotExist:
            print("🆕 No existing fee found, creating new one")
            
            # Create new
            serializer = self.get_serializer(data=request.data)
            action_type = "تم إنشاء"
        
        except SchoolFee.MultipleObjectsReturned:
            print("⚠️ Multiple fees found! This shouldn't happen with proper constraints")
            
            # Handle multiple records by getting the first one
            school_fee = SchoolFee.objects.filter(
                account=request.user.account,
                student_id=student_id,
                school_year_id=school_year_id
            ).first()
            
            serializer = self.get_serializer(school_fee, data=request.data, partial=True)
            action_type = "تم تعديل"
        
        print(f"🔧 Validating data with serializer...")
        
        if serializer.is_valid():
            print(f"✅ Data is valid, saving...")
            
            school_fee = serializer.save(
                account=request.user.account, 
                created_by=request.user
            )
            
            print(f"💾 Saved fee: ID={school_fee.id}, discount_percentage={school_fee.discount_percentage}, discount_amount={school_fee.discount_amount}")
            
            log_activity(
                user=request.user,
                account=request.user.account,
                note=f"{action_type} رسوم مدرسية للطالب",
                related_model='SchoolFee',
                related_id=str(school_fee.id)
            )
            
            response_data = serializer.data
            print(f"📤 Returning response: {response_data}")
            
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            print(f"❌ Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['patch'], url_path='toggle-clothes-payment')
    def toggle_clothes_payment(self, request):
        """Toggle clothes fee payment status for a specific student"""
        student_id = request.data.get('student_id')
        school_year_id = request.data.get('school_year_id')
        clothes_fee_paid = request.data.get('clothes_fee_paid', False)
        
        if not student_id or not school_year_id:
            return Response(
                {"error": "student_id and school_year_id are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            school_fee = SchoolFee.objects.get(
                account=request.user.account,
                student_id=student_id,
                school_year_id=school_year_id
            )
            
            school_fee.clothes_fee_paid = clothes_fee_paid
            school_fee.save(update_fields=['clothes_fee_paid'])
            
            log_activity(
                user=request.user,
                account=request.user.account,
                note=f"تم {'تأكيد' if clothes_fee_paid else 'إلغاء'} دفع رسوم الملابس للطالب {school_fee.student}",
                related_model='SchoolFee',
                related_id=str(school_fee.id)
            )
            
            serializer = self.get_serializer(school_fee)
            return Response(serializer.data)
            
        except SchoolFee.DoesNotExist:
            return Response(
                {"error": "School fee record not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='current-year-total')
    def current_year_total(self, request):
        account = request.user.account

        active_year = SchoolYear.objects.filter(account=account, is_active=True).first()
        if not active_year:
            return Response({"detail": "لا يوجد سنة دراسية مفعلة حالياً"}, status=404)

        # Get non-archived student IDs
        student_ids = Student.objects.filter(is_archived=False).values_list('id', flat=True)

        # Calculate total fees before discount
        total_fees_before_discount = ExpressionWrapper(
            F('school_fee') + F('books_fee') + F('trans_fee') + F('clothes_fee'),
            output_field=DecimalField()
        )

        # Calculate percentage discount
        percentage_discount = ExpressionWrapper(
            (F('school_fee') + F('books_fee') + F('trans_fee') + F('clothes_fee')) * 
            F('discount_percentage') / 100,
            output_field=DecimalField()
        )

        # Calculate total discount (percentage + fixed amount)
        total_discount = ExpressionWrapper(
            percentage_discount + F('discount_amount'),
            output_field=DecimalField()
        )

        # Calculate final total after discount (cannot be negative)
        # Use Greatest to ensure the result is never negative
        total_after_discount = ExpressionWrapper(
            Greatest(
                (F('school_fee') + F('books_fee') + F('trans_fee') + F('clothes_fee')) - 
                (((F('school_fee') + F('books_fee') + F('trans_fee') + F('clothes_fee')) * F('discount_percentage') / 100) + F('discount_amount')),
                Value(0)
            ),
            output_field=DecimalField()
        )

        # Get aggregated totals
        aggregated_data = (
            SchoolFee.objects
            .filter(account=account, school_year=active_year, student__in=student_ids)
            .annotate(
                total_before_discount=total_fees_before_discount,
                total_discount_amount=total_discount,
                total_after_discount=total_after_discount
            )
            .aggregate(
                total_before_discount_sum=Sum('total_before_discount'),
                total_discount_sum=Sum('total_discount_amount'),
                total_after_discount_sum=Sum('total_after_discount')
            )
        )

        return Response({
            "total_school_fees_before_discount": aggregated_data['total_before_discount_sum'] or 0,
            "total_discount_amount": aggregated_data['total_discount_sum'] or 0,
            "total_school_fees_after_discount": aggregated_data['total_after_discount_sum'] or 0,
            # Keep backward compatibility
            "total_school_fees": aggregated_data['total_after_discount_sum'] or 0
        })

    @action(detail=False, methods=['get', 'put'], url_path='default')
    def default_fee(self, request):
        if request.method == 'GET':
            try:
                fee = SchoolFee.objects.get(
                    account=request.user.account, 
                    school_class__isnull=True, 
                    student__isnull=True
                )
                serializer = self.get_serializer(fee)
                return Response(serializer.data)
            except SchoolFee.DoesNotExist:
                # Return default values with zeros instead of 404
                default_data = {
                    'id': None,
                    'school_fee': 0.00,
                    'books_fee': 0.00,
                    'trans_fee': 0.00,
                    'clothes_fee': 0.00,
                    'clothes_fee_paid': False,
                    'discount_percentage': 0.00,
                    'discount_amount': 0.00,
                    'school_class': None,
                    'student': None,
                    'school_year': None,
                    'created_at': None,
                    'year': None,
                    'total_fees_before_discount': 0.00,
                    'discount_amount_calculated': 0.00,
                    'total_fees_after_discount': 0.00
                }
                return Response(default_data, status=status.HTTP_200_OK)
        
        if request.method == 'PUT':
            fee, created = SchoolFee.objects.get_or_create(
                account=request.user.account,
                school_class=None,
                student=None,
                defaults={'created_by': request.user}
            )
            serializer = self.get_serializer(fee, data=request.data)
            if serializer.is_valid():
                updated = serializer.save(account=request.user.account)
                log_activity(
                    user=request.user,
                    account=request.user.account,
                    note="تم تعديل الرسوم الافتراضية" if not created else "تم إنشاء الرسوم الافتراضية",
                    related_model='SchoolFee',
                    related_id=str(updated.id)
                )
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='apply-discount')
    def apply_discount(self, request):
        """Apply discount to multiple students"""
        student_ids = request.data.get('student_ids', [])
        school_year_id = request.data.get('school_year_id')
        discount_percentage = request.data.get('discount_percentage', 0)
        discount_amount = request.data.get('discount_amount', 0)
        
        if not student_ids or not school_year_id:
            return Response(
                {"error": "student_ids and school_year_id are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate discount values
        if discount_percentage < 0 or discount_percentage > 100:
            return Response(
                {"error": "discount_percentage must be between 0 and 100"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if discount_amount < 0:
            return Response(
                {"error": "discount_amount cannot be negative"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = SchoolFee.objects.filter(
            account=request.user.account,
            student_id__in=student_ids,
            school_year_id=school_year_id
        ).update(
            discount_percentage=discount_percentage,
            discount_amount=discount_amount
        )
        
        log_activity(
            user=request.user,
            account=request.user.account,
            note=f"تم تطبيق خصم {discount_percentage}% + {discount_amount} على {updated_count} طالب",
            related_model='SchoolFee',
            related_id=None
        )
        
        return Response({
            "message": f"Discount applied to {updated_count} students",
            "updated_count": updated_count
        })
