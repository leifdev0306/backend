from .models import LiquidacionMensual
from datetime import date

def actualizar_liquidacion(viaje):
    """
    Actualiza la liquidación mensual correspondiente al mes y año del viaje completado.
    Suma ingresos, pasajeros y cuenta viaje completado.
    """
    fecha = viaje.fecha  # fecha del viaje (no la fecha actual)
    año = fecha.year
    mes = fecha.month
    entidad = viaje.entidad
    ingresos_viaje = viaje.precio * viaje.pasajeros_count
    pasajeros_viaje = viaje.pasajeros_count

    liquidacion, created = LiquidacionMensual.objects.get_or_create(
        entidad=entidad,
        año=año,
        mes=mes,
        defaults={
            'ingresos_totales': 0,
            'comision': 0,
            'total_pasajeros': 0,
            'total_viajes_completados': 0
        }
    )
    liquidacion.ingresos_totales += ingresos_viaje
    liquidacion.total_pasajeros += pasajeros_viaje
    liquidacion.total_viajes_completados += 1
    # Comisión = ingresos * porcentaje de comisión de la entidad
    liquidacion.comision = liquidacion.ingresos_totales * (entidad.comision_porcentaje / 100)
    liquidacion.save()