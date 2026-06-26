from django.core.exceptions import ValidationError
from django.utils import timezone

def validate_future_date(value):
    if value < timezone.now().date():
        raise ValidationError("La fecha de salida debe ser futura.")

def validate_positive_price(value):
    if value <= 0:
        raise ValidationError("El precio debe ser mayor que cero.")