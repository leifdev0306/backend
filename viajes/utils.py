from .models import LiquidacionMensual, HistorialEstado, Notificacion
from datetime import date
from django.utils import timezone
from django.db import transaction

def actualizar_liquidacion(viaje):
    """Actualiza la liquidación mensual con los datos del viaje completado."""
    fecha = viaje.fecha
    año = fecha.year
    mes = fecha.month
    entidad = viaje.entidad
    ingresos_viaje = viaje.precio * viaje.pasajeros_count
    pasajeros_viaje = viaje.pasajeros_count

    with transaction.atomic():
        liquidacion, created = LiquidacionMensual.objects.get_or_create(
            entidad=entidad,
            año=año,
            mes=mes,
            defaults={
                'ingresos_totales': 0,
                'comision': 0,
                'total_pasajeros': 0,
                'total_viajes': 0,
                'fecha_cierre': None
            }
        )
        liquidacion.ingresos_totales += ingresos_viaje
        liquidacion.total_pasajeros += pasajeros_viaje
        liquidacion.total_viajes += 1
        liquidacion.comision = liquidacion.ingresos_totales * (entidad.comision_porcentaje / 100)
        liquidacion.save()

def crear_historial_estado(viaje, estado_anterior, estado_nuevo, usuario=None, motivo=''):
    """Registra un cambio de estado en el historial."""
    HistorialEstado.objects.create(
        viaje=viaje,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario=usuario,
        motivo=motivo
    )

def enviar_notificacion(usuario, viaje, tipo, mensaje, datos_extra=None):
    """Crea una notificación para un usuario."""
    Notificacion.objects.create(
        usuario=usuario,
        viaje=viaje,
        tipo=tipo,
        mensaje=mensaje,
        datos_extra=datos_extra or {}
    )