from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import Account
from employees.models import EmployeeType  # adjust if needed

@receiver(post_save, sender=Account)
def create_default_employee_types(sender, instance, created, **kwargs):
    if created:
        default_types = [
            {'key': 'teacher', 'label': 'معلم/ة'},
            {'key': 'driver', 'label': 'سائق/ة'}
        ]
        for t in default_types:
            EmployeeType.objects.get_or_create(account=instance, key=t['key'], defaults={'label': t['label']})
