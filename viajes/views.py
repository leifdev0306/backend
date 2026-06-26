from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import *
from .serializers import *
from .permissions import IsEntidadOwner, IsAdminOrReadOnly
from .services import ViajeService, ReservaService, LiquidacionService
from .filters import ViajeFilter
import logging

logger = logging.getLogger(__name__)

# ---------- Provincia ----------
class ProvinciaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer
    permission_classes = [permissions.AllowAny]

# ---------- Entidad ----------
class EntidadViewSet(viewsets.ModelViewSet):
    queryset = Entidad.objects.all()
    serializer_class = EntidadSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Entidad.objects.all()
        if hasattr(user, 'entidad'):
            return Entidad.objects.filter(id=user.entidad.id)
        return Entidad.objects.none()

# ---------- Conductor ----------
class ConductorViewSet(viewsets.ModelViewSet):
    queryset = Conductor.objects.all()
    serializer_class = ConductorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Conductor.objects.all()
        if hasattr(user, 'entidad'):
            return Conductor.objects.filter(entidad=user.entidad)
        return Conductor.objects.none()

# ---------- Vehiculo ----------
class VehiculoViewSet(viewsets.ModelViewSet):
    queryset = Vehiculo.objects.all()
    serializer_class = VehiculoSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Vehiculo.objects.all()
        if hasattr(user, 'entidad'):
            return Vehiculo.objects.filter(entidad=user.entidad)
        return Vehiculo.objects.none()

# ---------- Ruta ----------
class RutaViewSet(viewsets.ModelViewSet):
    queryset = Ruta.objects.all()
    serializer_class = RutaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

# ---------- Viaje (con acciones personalizadas) ----------
class ViajeViewSet(viewsets.ModelViewSet):
    queryset = Viaje.objects.all()
    serializer_class = ViajeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ViajeFilter
    search_fields = ['descripcion']
    ordering_fields = ['fecha_salida', 'precio']
    ordering = ['fecha_salida']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = Viaje.objects.all()
        if user.is_superuser:
            return qs
        if hasattr(user, 'entidad'):
            return qs.filter(Q(entidad=user.entidad) | Q(estado='programado'))
        return qs.filter(estado='programado')

    def perform_create(self, serializer):
        serializer.save(entidad=self.request.user.entidad)

    # Acciones específicas
    @action(detail=True, methods=['post'])
    def reservar(self, request, pk=None):
        viaje = self.get_object()
        try:
            reserva = ReservaService.crear_reserva(viaje.id, request.data)
            return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancelar_reserva(self, request, pk=None):
        reserva_id = request.data.get('reserva_id')
        token = request.data.get('token')
        try:
            reserva = ReservaService.cancelar_reserva(reserva_id, token)
            return Response(ReservaSerializer(reserva).data)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def completar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.entidad.user != request.user:
            return Response({'detail': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        viaje.estado = 'completado'
        viaje.save()
        return Response(ViajeSerializer(viaje).data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.entidad.user != request.user:
            return Response({'detail': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        viaje.estado = 'cancelado'
        viaje.save()
        return Response(ViajeSerializer(viaje).data)

    @action(detail=True, methods=['get'])
    def pasajeros(self, request, pk=None):
        viaje = self.get_object()
        if viaje.entidad.user != request.user:
            return Response({'detail': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        reservas = viaje.reservas.filter(estado='confirmada')
        data = [{'nombre': r.nombre_cliente, 'carnet': r.carnet_cliente, 'asientos': r.asientos_reservados} for r in reservas]
        return Response(data)

    @action(detail=True, methods=['get'])
    def historial_estados(self, request, pk=None):
        # Simplificado: retorna el historial de cambios de estado (se podría implementar con un modelo de auditoría)
        return Response({'detail': 'Funcionalidad en desarrollo'})

# ---------- Reserva (adicional) ----------
class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Reserva.objects.all()
        if hasattr(user, 'entidad'):
            return Reserva.objects.filter(viaje__entidad=user.entidad)
        return Reserva.objects.none()

# ---------- Puntuacion ----------
class PuntuacionViewSet(viewsets.ModelViewSet):
    queryset = Puntuacion.objects.all()
    serializer_class = PuntuacionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        # Devuelve viajes completados sin puntuación por parte del usuario (requiere autenticación)
        # Implementación básica
        return Response({'detail': 'Funcionalidad en desarrollo'})

    @action(detail=False, methods=['post'])
    def calificar(self, request):
        # Recibe viaje_id, reserva_id, puntuacion, comentario
        viaje_id = request.data.get('viaje')
        reserva_id = request.data.get('reserva')
        puntuacion = request.data.get('puntuacion')
        comentario = request.data.get('comentario', '')
        try:
            reserva = Reserva.objects.get(id=reserva_id, viaje_id=viaje_id, estado='confirmada')
            if hasattr(reserva, 'puntuacion'):
                return Response({'detail': 'Ya calificado'}, status=status.HTTP_400_BAD_REQUEST)
            punt = Puntuacion.objects.create(
                viaje_id=viaje_id,
                reserva=reserva,
                puntuacion=puntuacion,
                comentario=comentario
            )
            return Response(PuntuacionSerializer(punt).data, status=status.HTTP_201_CREATED)
        except Reserva.DoesNotExist:
            return Response({'detail': 'Reserva no encontrada'}, status=status.HTTP_404_NOT_FOUND)

# ---------- Notificacion ----------
class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Notificacion.objects.all()
        if hasattr(user, 'entidad'):
            return Notificacion.objects.filter(entidad=user.entidad)
        return Notificacion.objects.filter(usuario=user)

# ---------- Liquidacion Mensual ----------
class LiquidacionMensualViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LiquidacionMensual.objects.all()
    serializer_class = LiquidacionMensualSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return LiquidacionMensual.objects.all()
        if hasattr(user, 'entidad'):
            return LiquidacionMensual.objects.filter(entidad=user.entidad)
        return LiquidacionMensual.objects.none()

    @action(detail=False, methods=['post'])
    def recalcular(self, request):
        # Recalcula liquidación para la entidad en un mes dado
        mes = request.data.get('mes')  # formato YYYY-MM-DD
        if not mes:
            return Response({'detail': 'Mes requerido'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            mes_date = datetime.strptime(mes, '%Y-%m-%d')
        except ValueError:
            return Response({'detail': 'Formato inválido'}, status=status.HTTP_400_BAD_REQUEST)
        entidad = request.user.entidad
        liquidacion = LiquidacionService.calcular_liquidacion_mensual(entidad.id, mes_date)
        return Response(LiquidacionMensualSerializer(liquidacion).data)

# ---------- Configuracion ----------
class ConfiguracionViewSet(viewsets.ModelViewSet):
    queryset = Configuracion.objects.all()
    serializer_class = ConfiguracionSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Configuracion.objects.all()
        if hasattr(user, 'entidad'):
            return Configuracion.objects.filter(Q(entidad=user.entidad) | Q(entidad=None))
        return Configuracion.objects.none()

# ---------- AdminStats (estadísticas globales) ----------
class AdminStatsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    def list(self, request):
        total_entidades = Entidad.objects.count()
        total_viajes = Viaje.objects.count()
        total_reservas = Reserva.objects.count()
        ingresos_totales = Reserva.objects.filter(estado='confirmada').aggregate(
            total=Sum('viaje__precio'))['total'] or 0
        return Response({
            'total_entidades': total_entidades,
            'total_viajes': total_viajes,
            'total_reservas': total_reservas,
            'ingresos_totales': ingresos_totales,
        })

    @action(detail=False, methods=['get'])
    def entidades_resumen(self, request):
        # Resumen por entidad
        data = Entidad.objects.annotate(
            total_viajes=Count('viajes'),
            total_reservas=Count('viajes__reservas'),
        ).values('id', 'nombre', 'total_viajes', 'total_reservas')
        return Response(data)

    @action(detail=False, methods=['get'])
    def detalle_mensual(self, request):
        # Detalle de ingresos por mes (para gráficos)
        from django.db.models.functions import TruncMonth
        data = Reserva.objects.filter(estado='confirmada') \
            .annotate(mes=TruncMonth('created_at')) \
            .values('mes') \
            .annotate(total=Sum('viaje__precio')) \
            .order_by('mes')
        return Response(data)

    @action(detail=True, methods=['post'])
    def suspender_entidad(self, request, pk=None):
        entidad = get_object_or_404(Entidad, pk=pk)
        entidad.is_active = False
        entidad.save()
        return Response({'detail': 'Entidad suspendida'})

    @action(detail=True, methods=['post'])
    def activar_entidad(self, request, pk=None):
        entidad = get_object_or_404(Entidad, pk=pk)
        entidad.is_active = True
        entidad.save()
        return Response({'detail': 'Entidad activada'})

# ---------- Promocion (para home) ----------
class PromocionViewSet(viewsets.ModelViewSet):
    queryset = Promocion.objects.all()
    serializer_class = PromocionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Promocion.objects.all()
        if hasattr(user, 'entidad'):
            return Promocion.objects.filter(entidad=user.entidad)
        return Promocion.objects.filter(activa=True)

# ---------- Home (endpoint especial) ----------
@action(detail=False, methods=['get'], url_path='home')
def home(self, request):
    data = ViajeService.get_home_data()
    return Response(data)