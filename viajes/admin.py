from django.contrib import admin
from .models import (
    Provincia, Entidad, Conductor, Vehiculo, Ruta,
    Viaje, Reserva, Puntuacion, Notificacion,
    LiquidacionMensual, Configuracion, Promocion
)

@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo')
    search_fields = ('nombre',)

@admin.register(Entidad)
class EntidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'user', 'provincia', 'is_active', 'fecha_registro')
    list_filter = ('is_active', 'provincia')
    search_fields = ('nombre', 'user__username', 'email')

@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'carnet', 'entidad', 'is_active')
    list_filter = ('is_active', 'entidad')
    search_fields = ('nombre', 'carnet')

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('placa', 'modelo', 'tipo', 'capacidad', 'entidad', 'is_active')
    list_filter = ('tipo', 'is_active', 'entidad')
    search_fields = ('placa', 'modelo')

@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display = ('origen', 'destino', 'distancia_km', 'duracion_estimada', 'activa')
    list_filter = ('activa', 'origen', 'destino')
    search_fields = ('origen__nombre', 'destino__nombre')

@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ('ruta', 'entidad', 'fecha_salida', 'precio', 'asientos_disponibles', 'estado')
    list_filter = ('estado', 'fecha_salida', 'entidad')
    search_fields = ('ruta__origen__nombre', 'ruta__destino__nombre', 'descripcion')
    date_hierarchy = 'fecha_salida'

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('nombre_cliente', 'carnet_cliente', 'viaje', 'asientos_reservados', 'estado')
    list_filter = ('estado', 'viaje__entidad')
    search_fields = ('nombre_cliente', 'carnet_cliente', 'email')
    readonly_fields = ('token_cancelacion',)

@admin.register(Puntuacion)
class PuntuacionAdmin(admin.ModelAdmin):
    list_display = ('viaje', 'reserva', 'puntuacion', 'fecha')
    list_filter = ('puntuacion',)

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'entidad', 'usuario', 'tipo', 'leida', 'fecha_envio')
    list_filter = ('tipo', 'leida', 'fecha_envio')
    search_fields = ('titulo', 'mensaje')

@admin.register(LiquidacionMensual)
class LiquidacionMensualAdmin(admin.ModelAdmin):
    list_display = ('entidad', 'mes', 'total_ingresos', 'total_viajes', 'neto')
    list_filter = ('entidad', 'mes')
    readonly_fields = ('fecha_calculo',)

@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ('clave', 'entidad', 'descripcion')
    list_filter = ('entidad',)
    search_fields = ('clave', 'valor')

@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'entidad', 'tipo', 'activa', 'fecha_inicio', 'fecha_fin')
    list_filter = ('tipo', 'activa', 'entidad')
    search_fields = ('titulo', 'descripcion')