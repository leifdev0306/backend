from django_filters import rest_framework as filters
from .models import Viaje

class ViajeFilter(filters.FilterSet):
    fecha_salida_desde = filters.DateTimeFilter(field_name='fecha_salida', lookup_expr='gte')
    fecha_salida_hasta = filters.DateTimeFilter(field_name='fecha_salida', lookup_expr='lte')
    precio_min = filters.NumberFilter(field_name='precio', lookup_expr='gte')
    precio_max = filters.NumberFilter(field_name='precio', lookup_expr='lte')
    origen = filters.NumberFilter(field_name='ruta__origen__id')
    destino = filters.NumberFilter(field_name='ruta__destino__id')
    estado = filters.CharFilter(field_name='estado', lookup_expr='exact')
    entidad = filters.NumberFilter(field_name='entidad__id')

    class Meta:
        model = Viaje
        fields = ['fecha_salida_desde', 'fecha_salida_hasta', 'precio_min', 'precio_max', 'origen', 'destino', 'estado', 'entidad']