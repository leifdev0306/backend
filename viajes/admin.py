from django.contrib import admin
from .models import Provincia, Entidad, Gestor, Viaje, Pasajero, Puntuacion, LiquidacionMensual

@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)

@admin.register(Entidad)
class EntidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'telefono', 'suspendida', 'puntuacion_promedio')  # Sin imagen_promocional
    list_filter = ('suspendida',)
    search_fields = ('nombre', 'telefono')

@admin.register(Gestor)
class GestorAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'entidad')
    list_filter = ('entidad',)
    search_fields = ('user__username',)

@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ('id', 'entidad', 'origen', 'destino', 'fecha', 'hora', 'estado', 'cupos_disponibles')
    list_filter = ('entidad', 'origen', 'destino', 'estado')
    search_fields = ('entidad__nombre', 'matricula')

@admin.register(Pasajero)
class PasajeroAdmin(admin.ModelAdmin):
    list_display = ('id', 'viaje', 'nombre_completo', 'ci', 'reservado_en')
    list_filter = ('viaje__entidad',)
    search_fields = ('nombre_completo', 'ci')

@admin.register(Puntuacion)
class PuntuacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'viaje', 'ci_cliente', 'valor', 'creado')
    list_filter = ('viaje__entidad', 'valor')
    search_fields = ('ci_cliente',)

@admin.register(LiquidacionMensual)
class LiquidacionMensualAdmin(admin.ModelAdmin):
    list_display = ('id', 'entidad', 'año', 'mes', 'ingresos_totales', 'comision', 'total_pasajeros', 'total_viajes_completados', 'pagada')
    list_filter = ('entidad', 'año', 'mes', 'pagada')
    search_fields = ('entidad__nombre',)