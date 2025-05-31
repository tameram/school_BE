# utils/services.py
from django.db import transaction
from .models import Counter

@transaction.atomic
def get_next_number(key: str, start: int = 10000000) -> int:
    counter, _ = Counter.objects.select_for_update().get_or_create(key=key, defaults={'value': start - 1})
    counter.value += 1
    counter.save()
    return counter.value