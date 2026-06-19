# viajes/views.py

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404
from datetime import datetime, date
from .models import Provincia, Viaje, Pasajero, Entidad, Gestor, LiquidacionMensual, Puntuacion
from .serializers import (
    ProvinciaSerializer, ViajeSerializer, PasajeroSerializer,
    GestorSerializer, EntidadSerializer, LiquidacionMensualSerializer,
    PuntuacionSerializer
)
from .permissions import IsGestor, IsAdmin
from .utils import actualizar_liquidacion


class ProvinciaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer
    permission_classes = [permissions.AllowAny]


class ViajeViewSet(viewsets.ModelViewSet):
    queryset = Viaje.objects.all()
    serializer_class = ViajeSerializer

    def get_permissions(self):
        if self.action in ['reservar', 'cancelar_reserva']:
            return [permissions.AllowAny()]
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'agregar_pasajero', 'completar', 'cancelar', 'pasajeros']:
            return [IsGestor()]
        if self.action == 'listar_activos':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        user = self.request.user
        if self.action in ['reservar', 'cancelar_reserva']:
            return Viaje.objects.all()
        if user.is_staff:
            return Viaje.objects.all()
        if hasattr(user, 'gestor'):
            return Viaje.objects.filter(entidad=user.gestor.entidad)
        return Viaje.objects.none()

    def perform_create(self, serializer):
        entidad = self.request.user.gestor.entidad
        serializer.save(entidad=entidad)

    def perform_update(self, serializer):
        entidad = self.request.user.gestor.entidad
        serializer.save(entidad=entidad)

    @action(detail=False, methods=['get'], url_path='activos')
    def listar_activos(self, request):
        origen = request.query_params.get('origen')
        destino = request.query_params.get('destino')
        ahora = datetime.now()
        qs = Viaje.objects.filter(
            estado__in=['activo', 'lleno'],
            entidad__suspendida=False,
            fecha__gt=ahora.date()
        ).exclude(
            Q(fecha=ahora.date()) & Q(hora__lt=ahora.time())
        )
        if origen:
            qs = qs.filter(origen_id=origen)
        if destino:
            qs = qs.filter(destino_id=destino)
        serializer = self.get_serializer(qs, many=True)
        # Añadir puntuación de la entidad (ya incluida en el serializador)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def reservar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.estado != 'activo':
            return Response({'error': 'El viaje no está activo'}, status=status.HTTP_400_BAD_REQUEST)
        if viaje.entidad.suspendida:
            return Response({'error': 'La entidad está suspendida'}, status=status.HTTP_400_BAD_REQUEST)
        if viaje.cupos_disponibles <= 0:
            return Response({'error': 'No hay cupos disponibles'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PasajeroSerializer(data={
            'viaje': viaje.id,
            'nombre_completo': request.data.get('nombre_completo'),
            'ci': request.data.get('ci')
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if viaje.cupos_disponibles == 0:
            viaje.estado = 'lleno'
            viaje.save(update_fields=['estado'])

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def cancelar_reserva(self, request, pk=None):
        viaje = self.get_object()
        ci = request.data.get('ci')
        if not ci:
            return Response({'error': 'Se necesita el número de CI'}, status=status.HTTP_400_BAD_REQUEST)
        pasajero = viaje.reservas.filter(ci=ci).first()
        if not pasajero:
            return Response({'error': 'No se encontró reserva con ese CI'}, status=status.HTTP_404_NOT_FOUND)
        pasajero.delete()
        if viaje.estado == 'lleno' and viaje.cupos_disponibles > 0:
            viaje.estado = 'activo'
            viaje.save(update_fields=['estado'])
        return Response({'status': 'reserva cancelada'})

    @action(detail=True, methods=['post'], permission_classes=[IsGestor])
    def agregar_pasajero(self, request, pk=None):
        viaje = self.get_object()
        serializer = PasajeroSerializer(data={
            'viaje': viaje.id,
            'nombre_completo': request.data.get('nombre_completo'),
            'ci': request.data.get('ci')
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if viaje.cupos_disponibles == 0:
            viaje.estado = 'lleno'
            viaje.save(update_fields=['estado'])
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsGestor])
    def completar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.estado != 'en_curso':
            return Response({'error': 'Solo se puede completar un viaje en curso'}, status=status.HTTP_400_BAD_REQUEST)
        viaje.estado = 'completado'
        viaje.save(update_fields=['estado'])
        actualizar_liquidacion(viaje)
        return Response({'status': 'completado'})

    @action(detail=True, methods=['post'], permission_classes=[IsGestor])
    def cancelar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.estado in ['completado', 'cancelado']:
            return Response({'error': 'No se puede cancelar este viaje'}, status=status.HTTP_400_BAD_REQUEST)
        viaje.estado = 'cancelado'
        viaje.save(update_fields=['estado'])
        return Response({'status': 'cancelado'})

    @action(detail=True, methods=['get'], permission_classes=[IsGestor])
    def pasajeros(self, request, pk=None):
        viaje = self.get_object()
        pasajeros = viaje.reservas.all()
        serializer = PasajeroSerializer(pasajeros, many=True)
        return Response(serializer.data)


class GestorViewSet(viewsets.ModelViewSet):
    queryset = Gestor.objects.all()
    serializer_class = GestorSerializer
    permission_classes = [IsAdmin]


class EntidadViewSet(viewsets.ModelViewSet):
    queryset = Entidad.objects.all()
    serializer_class = EntidadSerializer
    permission_classes = [IsAdmin]


class LiquidacionMensualViewSet(viewsets.ModelViewSet):
    queryset = LiquidacionMensual.objects.all()
    serializer_class = LiquidacionMensualSerializer
    permission_classes = [IsAdmin]

    @action(detail=True, methods=['post'])
    def marcar_pagada(self, request, pk=None):
        liquidacion = self.get_object()
        liquidacion.pagada = True
        liquidacion.save(update_fields=['pagada'])
        return Response({'status': 'pagada'})

    @action(detail=True, methods=['post'])
    def marcar_no_pagada(self, request, pk=None):
        liquidacion = self.get_object()
        liquidacion.pagada = False
        liquidacion.save(update_fields=['pagada'])
        entidad = liquidacion.entidad
        entidad.suspendida = True
        entidad.save(update_fields=['suspendida'])
        return Response({'status': 'no pagada, entidad suspendida'})


# ==================== VISTAS PARA ADMINISTRADOR (ESTADÍSTICAS) ====================
class AdminStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAdmin]

    def list(self, request):
        total_ingresos = LiquidacionMensual.objects.aggregate(Sum('ingresos_totales'))['ingresos_totales__sum'] or 0
        total_comision = LiquidacionMensual.objects.aggregate(Sum('comision'))['comision__sum'] or 0
        entidades = Entidad.objects.all()
        total_entidades = entidades.count()
        total_gestores = Gestor.objects.count()
        entidades_suspendidas = entidades.filter(suspendida=True).count()

        hoy = date.today()
        ultimos_meses = []
        for i in range(6):
            mes = hoy.month - i
            año = hoy.year
            if mes <= 0:
                mes += 12
                año -= 1
            total = LiquidacionMensual.objects.filter(año=año, mes=mes).aggregate(Sum('ingresos_totales'))['ingresos_totales__sum'] or 0
            ultimos_meses.append({
                'año': año,
                'mes': mes,
                'ingresos': float(total)
            })
        ultimos_meses.reverse()

        return Response({
            'total_ingresos': float(total_ingresos),
            'total_comision': float(total_comision),
            'total_entidades': total_entidades,
            'total_gestores': total_gestores,
            'entidades_suspendidas': entidades_suspendidas,
            'ingresos_mensuales': ultimos_meses,
        })

    @action(detail=False, methods=['get'], url_path='entidades-resumen')
    def entidades_resumen(self, request):
        entidades = Entidad.objects.all()
        resultado = []
        for entidad in entidades:
            liquidaciones = LiquidacionMensual.objects.filter(entidad=entidad)
            ingresos = liquidaciones.aggregate(Sum('ingresos_totales'))['ingresos_totales__sum'] or 0
            comision = liquidaciones.aggregate(Sum('comision'))['comision__sum'] or 0
            ultima_liquidacion = liquidaciones.order_by('-año', '-mes').first()
            resultado.append({
                'id': entidad.id,
                'nombre': entidad.nombre,
                'telefono': entidad.telefono,
                'comision_porcentaje': float(entidad.comision_porcentaje),
                'suspendida': entidad.suspendida,
                'ingresos_totales': float(ingresos),
                'comision_total': float(comision),
                'ultima_liquidacion': {
                    'año': ultima_liquidacion.año if ultima_liquidacion else None,
                    'mes': ultima_liquidacion.mes if ultima_liquidacion else None,
                    'pagada': ultima_liquidacion.pagada if ultima_liquidacion else None,
                } if ultima_liquidacion else None
            })
        return Response(resultado)

    @action(detail=True, methods=['post'], url_path='suspender')
    def suspender_entidad(self, request, pk=None):
        entidad = get_object_or_404(Entidad, pk=pk)
        entidad.suspendida = True
        entidad.save(update_fields=['suspendida'])
        return Response({'status': 'suspendida'})

    @action(detail=True, methods=['post'], url_path='activar')
    def activar_entidad(self, request, pk=None):
        entidad = get_object_or_404(Entidad, pk=pk)
        entidad.suspendida = False
        entidad.save(update_fields=['suspendida'])
        return Response({'status': 'activada'})


# ==================== VISTAS PARA PUNTUACIONES ====================
class PuntuacionViewSet(viewsets.ModelViewSet):
    queryset = Puntuacion.objects.all()
    serializer_class = PuntuacionSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'], url_path='pendientes')
    def pendientes(self, request):
        ci = request.query_params.get('ci')
        if not ci:
            return Response({'error': 'Se necesita el CI'}, status=status.HTTP_400_BAD_REQUEST)
        viajes_completados = Viaje.objects.filter(
            estado='completado',
            reservas__ci=ci
        ).exclude(
            puntuaciones__ci_cliente=ci
        ).distinct()
        serializer = ViajeSerializer(viajes_completados, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='calificar')
    def calificar(self, request):
        ci = request.data.get('ci')
        viaje_id = request.data.get('viaje_id')
        valor = request.data.get('valor')
        comentario = request.data.get('comentario', '')
        if not all([ci, viaje_id, valor]):
            return Response({'error': 'Faltan datos'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            viaje = Viaje.objects.get(id=viaje_id, estado='completado')
        except Viaje.DoesNotExist:
            return Response({'error': 'Viaje no encontrado o no completado'}, status=status.HTTP_404_NOT_FOUND)
        if not viaje.reservas.filter(ci=ci).exists():
            return Response({'error': 'No tienes una reserva en este viaje'}, status=status.HTTP_403_FORBIDDEN)
        if Puntuacion.objects.filter(viaje=viaje, ci_cliente=ci).exists():
            return Response({'error': 'Ya has puntuado este viaje'}, status=status.HTTP_400_BAD_REQUEST)
        puntuacion = Puntuacion.objects.create(
            viaje=viaje,
            ci_cliente=ci,
            valor=valor,
            comentario=comentario
        )
        viaje.entidad.recalcular_puntuacion()
        serializer = PuntuacionSerializer(puntuacion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)