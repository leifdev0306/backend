from .models import LiquidacionMensual
from datetime import date

def actualizar_liquidacion(viaje):
    """Suma los ingresos del viaje completado a la liquidación del mes actual"""
    hoy = date.today()
    año = hoy.year
    mes = hoy.month
    entidad = viaje.entidad
    ingresos_viaje = viaje.precio * viaje.pasajeros_count
    liquidacion, created = LiquidacionMensual.objects.get_or_create(
        entidad=entidad, año=año, mes=mes,
        defaults={'ingresos_totales': 0}
    )
    liquidacion.ingresos_totales += ingresos_viaje
    liquidacion.save()
    