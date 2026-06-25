from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProvinciaViewSet, ViajeViewSet, GestorViewSet,
    EntidadViewSet, ConductorViewSet, VehiculoViewSet,
    RutaViewSet, LiquidacionMensualViewSet, PuntuacionViewSet,
    NotificacionViewSet, ConfiguracionViewSet, AdminStatsViewSet,
    health_check, update_viajes_estados
)

router = DefaultRouter()
router.register(r'provincias', ProvinciaViewSet)
router.register(r'viajes', ViajeViewSet)
router.register(r'gestores', GestorViewSet)
router.register(r'entidades', EntidadViewSet)
router.register(r'conductores', ConductorViewSet)
router.register(r'vehiculos', VehiculoViewSet)
router.register(r'rutas', RutaViewSet)
router.register(r'liquidaciones', LiquidacionMensualViewSet)
router.register(r'puntuaciones', PuntuacionViewSet)
router.register(r'notificaciones', NotificacionViewSet)
router.register(r'configuraciones', ConfiguracionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Acciones específicas
    path('viajes/<int:pk>/reservar/', ViajeViewSet.as_view({'post': 'reservar'}), name='viaje-reservar'),
    path('viajes/<int:pk>/cancelar_reserva/', ViajeViewSet.as_view({'post': 'cancelar_reserva'}), name='viaje-cancelar-reserva'),
    path('viajes/<int:pk>/completar/', ViajeViewSet.as_view({'post': 'completar'}), name='viaje-completar'),
    path('viajes/<int:pk>/cancelar/', ViajeViewSet.as_view({'post': 'cancelar'}), name='viaje-cancelar'),
    path('viajes/<int:pk>/pasajeros/', ViajeViewSet.as_view({'get': 'pasajeros'}), name='viaje-pasajeros'),
    path('viajes/<int:pk>/historial-estados/', ViajeViewSet.as_view({'get': 'historial_estados'}), name='viaje-historial-estados'),
    path('puntuaciones/pendientes/', PuntuacionViewSet.as_view({'get': 'pendientes'}), name='puntuaciones-pendientes'),
    path('puntuaciones/calificar/', PuntuacionViewSet.as_view({'post': 'calificar'}), name='puntuaciones-calificar'),
    # Admin
    path('admin/stats/', AdminStatsViewSet.as_view({'get': 'list'}), name='admin-stats'),
    path('admin/entidades-resumen/', AdminStatsViewSet.as_view({'get': 'entidades_resumen'}), name='admin-entidades-resumen'),
    path('admin/detalle-mensual/', AdminStatsViewSet.as_view({'get': 'detalle_mensual'}), name='admin-detalle-mensual'),
    path('admin/entidades/<int:pk>/suspender/', AdminStatsViewSet.as_view({'post': 'suspender_entidad'}), name='admin-entidad-suspender'),
    path('admin/entidades/<int:pk>/activar/', AdminStatsViewSet.as_view({'post': 'activar_entidad'}), name='admin-entidad-activar'),
    # Utils
    path('admin/actualizar-estados/', update_viajes_estados, name='update-viajes-estados'),
    path('health/', health_check, name='health_check'),
]