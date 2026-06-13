from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from .models import Provincia, Viaje, Pasajero, Entidad, Gestor, LiquidacionMensual
from .serializers import (ProvinciaSerializer, ViajeSerializer, PasajeroSerializer,
                          GestorSerializer, EntidadSerializer, LiquidacionMensualSerializer)
from .permissions import IsGestor, IsAdmin

class ProvinciaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer
    permission_classes = [permissions.AllowAny]

class ViajeViewSet(viewsets.ModelViewSet):
    queryset = Viaje.objects.all()
    serializer_class = ViajeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['origen__nombre', 'destino__nombre']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsGestor]
        elif self.action == 'listar_activos':
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Viaje.objects.all()
        if hasattr(user, 'gestor'):
            return Viaje.objects.filter(entidad=user.gestor.entidad)
        return Viaje.objects.none()

    @action(detail=False, methods=['get'], url_path='activos')
    def listar_activos(self, request):
        origen = request.query_params.get('origen')
        destino = request.query_params.get('destino')
        ahora = datetime.now()
        # Solo viajes activos, de entidades no suspendidas, y que no hayan pasado la hora
        qs = Viaje.objects.filter(
            estado='activo',
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
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def reservar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.estado != 'activo' or viaje.entidad.suspendida:
            return Response({'error': 'Viaje no disponible'}, status=400)
        if viaje.cupos_disponibles <= 0:
            return Response({'error': 'Sin cupos'}, status=400)
        serializer = PasajeroSerializer(data={
            'viaje': viaje.id,
            'nombre_completo': request.data.get('nombre_completo'),
            'ci': request.data.get('ci')
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Actualizar estado del viaje si se llena
        if viaje.cupos_disponibles == 0:
            viaje.estado = 'lleno'
            viaje.save()
        return Response(serializer.data, status=201)

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
            viaje.save()
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['post'], permission_classes=[IsGestor])
    def completar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.estado != 'en_curso':
            return Response({'error': 'Solo se puede completar un viaje en curso'}, status=400)
        viaje.estado = 'completado'
        viaje.save()
        # Actualizar ingresos en la liquidación correspondiente
        from .utils import actualizar_liquidacion
        actualizar_liquidacion(viaje)
        return Response({'status': 'completado'})

    @action(detail=True, methods=['post'], permission_classes=[IsGestor])
    def cancelar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.estado in ['completado', 'cancelado']:
            return Response({'error': 'No se puede cancelar'}, status=400)
        viaje.estado = 'cancelado'
        viaje.save()
        return Response({'status': 'cancelado'})

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
        liquidacion.save()
        # Si se paga, reactivar entidad? Mejor lo haces manualmente desde admin
        return Response({'status': 'pagada'})

    @action(detail=True, methods=['post'])
    def marcar_no_pagada(self, request, pk=None):
        liquidacion = self.get_object()
        liquidacion.pagada = False
        liquidacion.save()
        # Suspender entidad automáticamente (desactivar viajes activos)
        entidad = liquidacion.entidad
        entidad.suspendida = True
        entidad.save()
        return Response({'status': 'no pagada, entidad suspendida'})