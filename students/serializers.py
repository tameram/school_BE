from rest_framework import serializers
from .models import Student, SchoolClass, StudentHistory, Bus


class StudentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentHistory
        fields = ['id', 'event', 'note', 'date']
class StudentSerializer(serializers.ModelSerializer):
    history = StudentHistorySerializer(many=True, read_only=True)
    class Meta:
        model = Student
        fields = '__all__'

class BusSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Bus
        fields = [
            'id', 'name', 'bus_number', 'bus_type',
            'capacity', 'phone_number', 'manager_name', 'student_count'
        ]

    def get_student_count(self, obj):
        return obj.students.count()

class SchoolClassListSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'student_count']

    def get_student_count(self, obj):
        return obj.students.count()

class SchoolClassDetailSerializer(serializers.ModelSerializer):
    students = StudentSerializer(many=True, read_only=True)

    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'students']
