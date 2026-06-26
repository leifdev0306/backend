import secrets
import string
from django.http import JsonResponse
from django.utils import timezone
from .models import Viaje

def generate_cancellation_token(length=32):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def update_viajes_estados(request):
    """Actualiza viajes programados a activos si ya pasó la fecha de salida"""
    now = timezone.now()
    viajes = Viaje.objects.filter(estado='programado', fecha_salida__lte=now)
    count = viajes.update(estado='activo')
    return JsonResponse({'actualizados': count})

def health_check(request):
    return JsonResponse({'status': 'ok'})