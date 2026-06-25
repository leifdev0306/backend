from rest_framework import viewsets, status, permissions, parsers, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, Count, Avg
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, date, timedelta
from .models import (
    Provincia, Viaje, Pasajero, Entidad, Gestor, Conductor, Vehiculo,
    Ruta, Puntuacion, LiquidacionMensual, HistorialEstado, Notificacion,
    Configuracion
)
from .serializers import (
    ProvinciaSerializer, ViajeSerializer, PasajeroSerializer,
    GestorSerializer, EntidadSerializer, ConductorSerializer,
    VehiculoSerializer, RutaSerializer, PuntuacionSerializer,
    LiquidacionMensualSerializer, HistorialEstadoSerializer,
    NotificacionSerializer, ConfiguracionSerializer
)
from .permissions import IsGestor, IsAdmin, IsGestorOrAdmin
from .utils import (
    actualizar_liquidacion, crear_historial_estado, enviar_notificacion,
    enviar_email_notificacion, obtener_configuracion
)
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
import logging

logger = logging.getLogger(__name__)

# ==================== PAGINACIÓN ====================
class ViajePagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50

class EntidadPagination(PageNumberPagination):
    page_size = 10

# ==================== HEALTH CHECK ====================
def health_check(request):
    return JsonResponse({"status": "ok", "timestamp": datetime.now().isoformat()})

def update_viajes_estados(request):
    """Actualiza automáticamente los estados de los viajes."""
    ahora = timezone.now()
    activos = Viaje.objects.filter(
        estado__in=['activo', 'lleno'],
        fecha__lt=ahora.date()
    ).exclude(
        Q(fecha=ahora.date()) & Q(hora__gt=ahora.time())
    )
    activos_hoy = Viaje.objects.filter(
        estado__in=['activo', 'lleno'],
        fecha=ahora.date(),
        hora__lte=ahora.time()
    )
    activos_a_actualizar = (activos | activos_hoy).distinct()
    count_activos = activos_a_actualizar.count()
    for viaje in activos_a_actualizar:
        viaje.estado = 'en_curso'
        viaje.save(update_fields=['estado'])
        crear_historial_estado(viaje, 'activo/lleno', 'en_curso', motivo='Actualización automática por hora de salida')

    # En curso → Completado (después de 30 minutos)
    tiempo_limite = ahora - timedelta(minutes=30)
    en_curso = Viaje.objects.filter(
        estado='en_curso',
        fecha__lt=ahora.date()
    ).exclude(
        Q(fecha=ahora.date()) & Q(hora__gt=tiempo_limite.time())
    )
    en_curso_hoy = Viaje.objects.filter(
        estado='en_curso',
        fecha=ahora.date(),
        hora__lte=tiempo_limite.time()
    )
    en_curso_a_actualizar = (en_curso | en_curso_hoy).distinct()
    count_en_curso = en_curso_a_actualizar.count()
    for viaje in en_curso_a_actualizar:
        viaje.estado = 'completado'
        viaje.save(update_fields=['estado'])
        crear_historial_estado(viaje, 'en_curso', 'completado', motivo='Actualización automática por tiempo')
        actualizar_liquidacion(viaje)

    return JsonResponse({
        'status': 'ok',
        'updated_activos': count_activos,
        'updated_en_curso': count_en_curso,
        'message': f'Actualizados {count_activos} a "en_curso" y {count_en_curso} a "completado".'
    })

# ==================== VIEWSETS ====================
class ProvinciaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer
    permission_classes = [permissions.AllowAny]

class EntidadViewSet(viewsets.ModelViewSet):
    queryset = Entidad.objects.all()
    serializer_class = EntidadSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser)
    pagination_class = EntidadPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['nombre', 'telefono', 'email']
    filterset_fields = ['suspendida', 'activa', 'plan']

    def get_permissions(self):
        if self.action == 'mi_entidad':
            return [permissions.IsAuthenticated()]
        if self.request.method in ['PUT', 'PATCH'] and self.action not in ['create', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Entidad.objects.all()
        if hasattr(user, 'gestor'):
            return Entidad.objects.filter(id=user.gestor.entidad.id)
        return Entidad.objects.none()

    def perform_update(self, serializer):
        user = self.request.user
        if hasattr(user, 'gestor'):
            entidad = user.gestor.entidad
            if serializer.instance.id != entidad.id:
                raise PermissionDenied("No puedes modificar otra entidad")
        serializer.save()

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def mi_entidad(self, request):
        user = request.user
        if hasattr(user, 'gestor'):
            entidad = user.gestor.entidad
            serializer = self.get_serializer(entidad, context={'request': request})
            return Response(serializer.data)
        return Response({'error': 'No eres gestor'}, status=status.HTTP_403_FORBIDDEN)

class ViajeViewSet(viewsets.ModelViewSet):
    queryset = Viaje.objects.all()
    serializer_class = ViajeSerializer
    pagination_class = ViajePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['origen', 'destino', 'estado', 'entidad', 'fecha', 'tipo_vehiculo']
    search_fields = ['origen__nombre', 'destino__nombre', 'entidad__nombre', 'lugar_salida', 'lugar_llegada']
    ordering_fields = ['fecha', 'hora', 'precio']
    ordering = ['fecha', 'hora']

    def get_permissions(self):
        if self.action in ['reservar', 'cancelar_reserva']:
            return [permissions.AllowAny()]
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'agregar_pasajero', 'completar', 'cancelar', 'pasajeros',
                           'historial_estados']:
            return [IsGestorOrAdmin()]
        if self.action == 'listar_activos':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        user = self.request.user
        qs = Viaje.objects.select_related('origen', 'destino', 'entidad', 'conductor', 'vehiculo', 'ruta')
        if self.action in ['reservar', 'cancelar_reserva']:
            return qs
        if user.is_staff:
            return qs
        if hasattr(user, 'gestor'):
            return qs.filter(entidad=user.gestor.entidad)
        return qs.none()

    def perform_create(self, serializer):
        entidad = self.request.user.gestor.entidad
        serializer.save(entidad=entidad)

    @action(detail=False, methods=['get'], url_path='activos')
    def listar_activos(self, request):
        origen = request.query_params.get('origen')
        destino = request.query_params.get('destino')
        fecha = request.query_params.get('fecha')
        ahora = timezone.now()
        qs = Viaje.objects.select_related('origen', 'destino', 'entidad').filter(
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
        if fecha:
            try:
                fecha_parsed = datetime.strptime(fecha, '%Y-%m-%d').date()
                qs = qs.filter(fecha=fecha_parsed)
            except ValueError:
                pass
        qs = qs.order_by('fecha', 'hora')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
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

        ci = request.data.get('ci')
        nombre = request.data.get('nombre_completo')
        if not ci or not nombre:
            return Response({'error': 'Nombre y CI son obligatorios'}, status=status.HTTP_400_BAD_REQUEST)

        if Pasajero.objects.filter(viaje=viaje, ci=ci).exists():
            return Response({'error': 'Ya tienes una reserva en este viaje'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PasajeroSerializer(data={
            'viaje': viaje.id,
            'nombre_completo': nombre,
            'ci': ci,
            'telefono_contacto': request.data.get('telefono_contacto', ''),
            'email': request.data.get('email', ''),
            'asiento_asignado': request.data.get('asiento_asignado', ''),
            'confirmado': True,
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if viaje.cupos_disponibles == 0:
            viaje.estado = 'lleno'
            viaje.save(update_fields=['estado'])

        # Notificar al gestor
        gestores = viaje.entidad.gestores.all()
        for gestor in gestores:
            if gestor.notificaciones_email:
                enviar_notificacion(
                    usuario=gestor.user,
                    viaje=viaje,
                    tipo='reserva',
                    mensaje=f'Nueva reserva de {nombre} para {viaje.origen} → {viaje.destino}'
                )
                enviar_email_notificacion(
                    gestor.user,
                    f'Nueva reserva - {viaje.numero_viaje}',
                    f'El pasajero {nombre} ha reservado en el viaje {viaje.numero_viaje}'
                )

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

        ahora = timezone.now()
        salida = timezone.make_aware(datetime.combine(viaje.fecha, viaje.hora))
        if (salida - ahora).total_seconds() < 7200:  # menos de 2 horas
            crear_historial_estado(
                viaje, 'reserva', 'cancelado_tarde',
                usuario=request.user if request.user.is_authenticated else None,
                motivo=f'Cancelado por {pasajero.nombre_completo} ({ci}) - dentro de 2 horas'
            )
        else:
            crear_historial_estado(
                viaje, 'reserva', 'cancelado',
                usuario=request.user if request.user.is_authenticated else None,
                motivo=f'Cancelado por {pasajero.nombre_completo} ({ci})'
            )

        pasajero.delete()
        if viaje.estado == 'lleno' and viaje.cupos_disponibles > 0:
            viaje.estado = 'activo'
            viaje.save(update_fields=['estado'])

        return Response({'status': 'reserva cancelada'})

    @action(detail=True, methods=['post'], permission_classes=[IsGestorOrAdmin])
    def agregar_pasajero(self, request, pk=None):
        viaje = self.get_object()
        ci = request.data.get('ci')
        if not ci:
            return Response({'error': 'CI obligatorio'}, status=status.HTTP_400_BAD_REQUEST)
        if Pasajero.objects.filter(viaje=viaje, ci=ci).exists():
            return Response({'error': 'Ya existe un pasajero con ese CI'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PasajeroSerializer(data={
            'viaje': viaje.id,
            'nombre_completo': request.data.get('nombre_completo'),
            'ci': ci,
            'telefono_contacto': request.data.get('telefono_contacto', ''),
            'email': request.data.get('email', ''),
            'asiento_asignado': request.data.get('asiento_asignado', ''),
            'confirmado': True,
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if viaje.cupos_disponibles == 0:
            viaje.estado = 'lleno'
            viaje.save(update_fields=['estado'])
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsGestorOrAdmin])
    def completar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.estado != 'en_curso':
            return Response({'error': 'Solo se puede completar un viaje en curso'}, status=status.HTTP_400_BAD_REQUEST)
        viaje.estado = 'completado'
        viaje.save(update_fields=['estado'])
        crear_historial_estado(viaje, 'en_curso', 'completado', usuario=request.user)
        actualizar_liquidacion(viaje)
        return Response({'status': 'completado'})

    @action(detail=True, methods=['post'], permission_classes=[IsGestorOrAdmin])
    def cancelar(self, request, pk=None):
        viaje = self.get_object()
        if viaje.estado in ['completado', 'cancelado', 'cancelado_tarde']:
            return Response({'error': 'No se puede cancelar este viaje'}, status=status.HTTP_400_BAD_REQUEST)
        estado_anterior = viaje.estado
        viaje.estado = 'cancelado'
        viaje.save(update_fields=['estado'])
        crear_historial_estado(viaje, estado_anterior, 'cancelado', usuario=request.user, motivo=request.data.get('motivo', ''))
        return Response({'status': 'cancelado'})

    @action(detail=True, methods=['get'], permission_classes=[IsGestorOrAdmin])
    def pasajeros(self, request, pk=None):
        viaje = self.get_object()
        pasajeros = viaje.reservas.all()
        serializer = PasajeroSerializer(pasajeros, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsGestorOrAdmin])
    def historial_estados(self, request, pk=None):
        viaje = self.get_object()
        historial = viaje.historial_estados.all().order_by('-fecha_cambio')
        serializer = HistorialEstadoSerializer(historial, many=True)
        return Response(serializer.data)

class ConductorViewSet(viewsets.ModelViewSet):
    queryset = Conductor.objects.all()
    serializer_class = ConductorSerializer
    permission_classes = [IsGestorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['nombre', 'cedula', 'telefono']
    filterset_fields = ['entidad', 'activo']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Conductor.objects.all()
        if hasattr(user, 'gestor'):
            return Conductor.objects.filter(entidad=user.gestor.entidad)
        return Conductor.objects.none()

    def perform_create(self, serializer):
        entidad = self.request.user.gestor.entidad
        serializer.save(entidad=entidad)

class VehiculoViewSet(viewsets.ModelViewSet):
    queryset = Vehiculo.objects.all()
    serializer_class = VehiculoSerializer
    permission_classes = [IsGestorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['placa', 'modelo']
    filterset_fields = ['entidad', 'tipo', 'estado']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Vehiculo.objects.all()
        if hasattr(user, 'gestor'):
            return Vehiculo.objects.filter(entidad=user.gestor.entidad)
        return Vehiculo.objects.none()

    def perform_create(self, serializer):
        entidad = self.request.user.gestor.entidad
        serializer.save(entidad=entidad)

class RutaViewSet(viewsets.ModelViewSet):
    queryset = Ruta.objects.all()
    serializer_class = RutaSerializer
    permission_classes = [IsGestorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['origen__nombre', 'destino__nombre']
    filterset_fields = ['activa']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Ruta.objects.all()
        if hasattr(user, 'gestor'):
            return Ruta.objects.all()  # Los gestores pueden ver todas las rutas, pero solo admin puede crear/modificar
        return Ruta.objects.none()

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            raise PermissionDenied("Solo administradores pueden crear rutas.")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.is_staff:
            raise PermissionDenied("Solo administradores pueden modificar rutas.")
        serializer.save()

class GestorViewSet(viewsets.ModelViewSet):
    queryset = Gestor.objects.all()
    serializer_class = GestorSerializer
    permission_classes = [IsAdmin]

class LiquidacionMensualViewSet(viewsets.ModelViewSet):
    queryset = LiquidacionMensual.objects.all()
    serializer_class = LiquidacionMensualSerializer
    permission_classes = [IsAdmin]

    @action(detail=True, methods=['post'])
    def marcar_pagada(self, request, pk=None):
        liquidacion = self.get_object()
        liquidacion.pagada = True
        liquidacion.fecha_cierre = timezone.now()
        liquidacion.save(update_fields=['pagada', 'fecha_cierre'])
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
        page = self.paginate_queryset(viajes_completados)
        if page is not None:
            serializer = ViajeSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ViajeSerializer(viajes_completados, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='calificar')
    def calificar(self, request):
        ci = request.data.get('ci')
        viaje_id = request.data.get('viaje_id')
        valor = request.data.get('valor')
        comentario = request.data.get('comentario', '')
        categoria = request.data.get('categoria', 'general')
        if not all([ci, viaje_id, valor]):
            return Response({'error': 'Faltan datos'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            viaje = Viaje.objects.get(id=viaje_id, estado='completado')
        except Viaje.DoesNotExist:
            return Response({'error': 'Viaje no encontrado o no completado'}, status=status.HTTP_404_NOT_FOUND)
        if not viaje.reservas.filter(ci=ci).exists():
            return Response({'error': 'No tienes una reserva en este viaje'}, status=status.HTTP_403_FORBIDDEN)
        if Puntuacion.objects.filter(viaje=viaje, ci_cliente=ci, categoria=categoria).exists():
            return Response({'error': 'Ya has puntuado este viaje en esta categoría'}, status=status.HTTP_400_BAD_REQUEST)
        puntuacion = Puntuacion.objects.create(
            viaje=viaje,
            ci_cliente=ci,
            valor=valor,
            comentario=comentario,
            categoria=categoria
        )
        viaje.entidad.recalcular_puntuacion()
        serializer = PuntuacionSerializer(puntuacion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user)

    @action(detail=True, methods=['post'])
    def marcar_leida(self, request, pk=None):
        notificacion = self.get_object()
        notificacion.leida = True
        notificacion.save(update_fields=['leida'])
        return Response({'status': 'leida'})

    @action(detail=False, methods=['post'])
    def marcar_todas_leidas(self, request):
        self.get_queryset().update(leida=True)
        return Response({'status': 'todas leidas'})

class ConfiguracionViewSet(viewsets.ModelViewSet):
    queryset = Configuracion.objects.all()
    serializer_class = ConfiguracionSerializer
    permission_classes = [IsAdmin]

class AdminStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAdmin]

    def list(self, request):
        total_ingresos = LiquidacionMensual.objects.aggregate(Sum('ingresos_totales'))['ingresos_totales__sum'] or 0
        total_comision = LiquidacionMensual.objects.aggregate(Sum('comision'))['comision__sum'] or 0
        total_pasajeros = LiquidacionMensual.objects.aggregate(Sum('total_pasajeros'))['total_pasajeros__sum'] or 0
        entidades = Entidad.objects.all()
        total_entidades = entidades.count()
        total_gestores = Gestor.objects.count()
        entidades_suspendidas = entidades.filter(suspendida=True).count()

        hoy = date.today()
        viajes_hoy = Viaje.objects.filter(fecha=hoy, estado__in=['activo', 'lleno']).count()

        ultimos_meses = []
        for i in range(6):
            mes = hoy.month - i
            año = hoy.year
            if mes <= 0:
                mes += 12
                año -= 1
            total = LiquidacionMensual.objects.filter(año=año, mes=mes).aggregate(
                ingresos=Sum('ingresos_totales'),
                pasajeros=Sum('total_pasajeros'),
                viajes=Sum('total_viajes')
            )
            ultimos_meses.append({
                'año': año,
                'mes': mes,
                'ingresos': float(total['ingresos'] or 0),
                'pasajeros': total['pasajeros'] or 0,
                'viajes': total['viajes'] or 0,
            })
        ultimos_meses.reverse()

        return Response({
            'total_ingresos': float(total_ingresos),
            'total_comision': float(total_comision),
            'total_pasajeros': total_pasajeros,
            'total_entidades': total_entidades,
            'total_gestores': total_gestores,
            'entidades_suspendidas': entidades_suspendidas,
            'viajes_hoy': viajes_hoy,
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
            pasajeros = liquidaciones.aggregate(Sum('total_pasajeros'))['total_pasajeros__sum'] or 0
            viajes = liquidaciones.aggregate(Sum('total_viajes'))['total_viajes__sum'] or 0
            ultima_liquidacion = liquidaciones.order_by('-año', '-mes').first()
            resultado.append({
                'id': entidad.id,
                'nombre': entidad.nombre,
                'telefono': entidad.telefono,
                'comision_porcentaje': float(entidad.comision_porcentaje),
                'suspendida': entidad.suspendida,
                'puntuacion_promedio': entidad.puntuacion_promedio,
                'ingresos_totales': float(ingresos),
                'comision_total': float(comision),
                'total_pasajeros': pasajeros,
                'total_viajes': viajes,
                'ultima_liquidacion': {
                    'año': ultima_liquidacion.año if ultima_liquidacion else None,
                    'mes': ultima_liquidacion.mes if ultima_liquidacion else None,
                    'pagada': ultima_liquidacion.pagada if ultima_liquidacion else None,
                } if ultima_liquidacion else None
            })
        return Response(resultado)

    @action(detail=False, methods=['get'], url_path='detalle-mensual')
    def detalle_mensual(self, request):
        año = request.query_params.get('año')
        mes = request.query_params.get('mes')
        hoy = date.today()
        if not año or not mes:
            año = str(hoy.year)
            mes = str(hoy.month)
        año = int(año)
        mes = int(mes)

        viajes_mes = Viaje.objects.filter(
            estado='completado',
            fecha__year=año,
            fecha__month=mes
        )
        total_ingresos = viajes_mes.aggregate(Sum('precio'))['precio__sum'] or 0
        total_pasajeros = viajes_mes.aggregate(Sum('pasajeros_count'))['pasajeros_count__sum'] or 0
        total_viajes = viajes_mes.count()

        entidades_data = []
        for entidad in Entidad.objects.all():
            viajes_entidad = viajes_mes.filter(entidad=entidad)
            if viajes_entidad.exists():
                entidades_data.append({
                    'entidad_id': entidad.id,
                    'entidad_nombre': entidad.nombre,
                    'viajes': viajes_entidad.count(),
                    'ingresos': float(viajes_entidad.aggregate(Sum('precio'))['precio__sum'] or 0),
                    'pasajeros': viajes_entidad.aggregate(Sum('pasajeros_count'))['pasajeros_count__sum'] or 0,
                })

        liquidaciones = LiquidacionMensual.objects.filter(año=año, mes=mes)
        pagadas = liquidaciones.filter(pagada=True).count()
        no_pagadas = liquidaciones.filter(pagada=False).count()

        return Response({
            'año': año,
            'mes': mes,
            'total_ingresos': float(total_ingresos),
            'total_pasajeros': total_pasajeros,
            'total_viajes': total_viajes,
            'entidades': entidades_data,
            'liquidaciones_pagadas': pagadas,
            'liquidaciones_no_pagadas': no_pagadas,
        })

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