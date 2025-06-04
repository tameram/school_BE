# inventory/serializers.py
from rest_framework import serializers
from .models import StoreItem

class StoreItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreItem
        fields = '__all__'
        read_only_fields = ['account']
