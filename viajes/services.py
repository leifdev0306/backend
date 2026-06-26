from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum, Count, Q
from .models import Viaje, Reserva, LiquidacionMensual, Entidad, Promocion
from .utils import generate_cancellation_token
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ViajeService:
    @staticmethod
    def get_home_data():
        """Datos para la home screen: promociones activas y viajes destacados"""
        cache_key = 'home_data'
        cached = cache.get(cache_key)
        if cached:
            return cached
        # Promociones activas
        promociones = Promocion.objects.filter(
            activa=True,
            fecha_inicio__lte=datetime.now(),
            fecha_fin__gte=datetime.now()
        ).select_related('entidad', 'viaje')
        # Viajes próximos (ordenados por fecha)
        viajes_destacados = Viaje.objects.filter(
            estado='programado',
            fecha_salida__gte=datetime.now()
        ).order_by('fecha_salida')[:10]
        data = {
            'promociones': PromocionSerializer(promociones, many=True).data,
            'viajes_destacados': ViajeSerializer(viajes_destacados, many=True).data,
        }
        cache.set(cache_key, data, 60*10)  # 10 min
        return data

class ReservaService:
    @staticmethod
    @transaction.atomic
    def crear_reserva(viaje_id, data):
        viaje = Viaje.objects.select_for_update().get(id=viaje_id)
        asientos = int(data.get('asientos_reservados', 0))
        if asientos <= 0:
            raise ValueError("Debe reservar al menos un asiento")
        if viaje.asientos_disponibles < asientos:
            raise ValueError("No hay suficientes asientos disponibles")
        viaje.actualizar_asientos(-asientos)
        token = generate_cancellation_token()
        reserva = Reserva.objects.create(
            viaje=viaje,
            nombre_cliente=data['nombre_cliente'],
            carnet_cliente=data['carnet_cliente'],
            telefono=data.get('telefono', ''),
            email=data.get('email', ''),
            asientos_reservados=asientos,
            token_cancelacion=token
        )
        logger.info(f"Reserva creada {reserva.id} para {reserva.nombre_cliente}")
        return reserva

    @staticmethod
    @transaction.atomic
    def cancelar_reserva(reserva_id, token=None):
        reserva = Reserva.objects.select_related('viaje').get(id=reserva_id)
        if token and reserva.token_cancelacion != token:
            raise ValueError("Token de cancelación inválido")
        reserva.cancelar(devolver_asientos=True)
        return reserva

class LiquidacionService:
    @staticmethod
    def calcular_liquidacion_mensual(entidad_id, mes):
        """Calcula la liquidación para una entidad en un mes específico"""
        fecha_inicio = datetime(mes.year, mes.month, 1)
        fecha_fin = fecha_inicio + timedelta(days=32)
        fecha_fin = fecha_fin.replace(day=1) - timedelta(days=1)
        viajes = Viaje.objects.filter(
            entidad_id=entidad_id,
            estado='completado',
            fecha_salida__gte=fecha_inicio,
            fecha_salida__lte=fecha_fin
        )
        total_ingresos = viajes.aggregate(Sum('precio'))['precio__sum'] or 0
        total_viajes = viajes.count()
        total_pasajeros = Reserva.objects.filter(
            viaje__in=viajes, estado='confirmada'
        ).aggregate(Sum('asientos_reservados'))['asientos_reservados__sum'] or 0
        comision = total_ingresos * 0.05  # ejemplo 5%
        neto = total_ingresos - comision
        liquidacion, created = LiquidacionMensual.objects.update_or_create(
            entidad_id=entidad_id,
            mes=fecha_inicio,
            defaults={
                'total_ingresos': total_ingresos,
                'total_viajes': total_viajes,
                'total_pasajeros': total_pasajeros,
                'comision': comision,
                'neto': neto,
            }
        )
        return liquidacion