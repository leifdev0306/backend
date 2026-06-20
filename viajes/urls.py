from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProvinciaViewSet, ViajeViewSet, GestorViewSet,
    EntidadViewSet, LiquidacionMensualViewSet, PuntuacionViewSet,
    AdminStatsViewSet, health_check  # 👈 IMPORTAMOS health_check
)

router = DefaultRouter()
router.register(r'provincias', ProvinciaViewSet)
router.register(r'viajes', ViajeViewSet)
router.register(r'gestores', GestorViewSet)
router.register(r'entidades', EntidadViewSet)
router.register(r'liquidaciones', LiquidacionMensualViewSet)
router.register(r'puntuaciones', PuntuacionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('viajes/<int:pk>/reservar/', ViajeViewSet.as_view({'post': 'reservar'}), name='viaje-reservar'),
    path('viajes/<int:pk>/cancelar_reserva/', ViajeViewSet.as_view({'post': 'cancelar_reserva'}), name='viaje-cancelar-reserva'),
    path('puntuaciones/pendientes/', PuntuacionViewSet.as_view({'get': 'pendientes'}), name='puntuaciones-pendientes'),
    path('puntuaciones/calificar/', PuntuacionViewSet.as_view({'post': 'calificar'}), name='puntuaciones-calificar'),

    # ADMIN STATS
    path('admin/stats/', AdminStatsViewSet.as_view({'get': 'list'}), name='admin-stats'),
    path('admin/entidades-resumen/', AdminStatsViewSet.as_view({'get': 'entidades_resumen'}), name='admin-entidades-resumen'),
    path('admin/detalle-mensual/', AdminStatsViewSet.as_view({'get': 'detalle_mensual'}), name='admin-detalle-mensual'),
    path('admin/entidades/<int:pk>/suspender/', AdminStatsViewSet.as_view({'post': 'suspender_entidad'}), name='admin-entidad-suspender'),
    path('admin/entidades/<int:pk>/activar/', AdminStatsViewSet.as_view({'post': 'activar_entidad'}), name='admin-entidad-activar'),

    # HEALTH CHECK (para mantener vivo el servidor)
    path('health/', health_check, name='health_check'),  # 👈 NUEVO ENDPOINT
]