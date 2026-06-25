from django.contrib import admin
from .models import (
    Provincia, Entidad, Gestor, Viaje, Pasajero, Conductor, Vehiculo,
    Ruta, Puntuacion, LiquidacionMensual, HistorialEstado, Notificacion,
    Configuracion
)

@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)

@admin.register(Entidad)
class EntidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'telefono', 'email', 'suspendida', 'activa', 'plan', 'puntuacion_promedio')
    list_filter = ('suspendida', 'activa', 'plan')
    search_fields = ('nombre', 'telefono', 'email')

@admin.register(Gestor)
class GestorAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'entidad', 'telefono')
    list_filter = ('entidad',)
    search_fields = ('user__username', 'user__email', 'entidad__nombre')

@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'cedula', 'telefono', 'entidad', 'activo')
    list_filter = ('entidad', 'activo')
    search_fields = ('nombre', 'cedula')

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('id', 'placa', 'tipo', 'modelo', 'capacidad', 'estado', 'entidad')
    list_filter = ('entidad', 'tipo', 'estado')
    search_fields = ('placa', 'modelo')

@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display = ('id', 'origen', 'destino', 'distancia_km', 'tiempo_estimado_min', 'activa')
    list_filter = ('activa',)
    search_fields = ('origen__nombre', 'destino__nombre')

@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero_viaje', 'entidad', 'origen', 'destino', 'fecha', 'hora', 'estado', 'cupos_disponibles')
    list_filter = ('entidad', 'origen', 'destino', 'estado', 'fecha')
    search_fields = ('numero_viaje', 'matricula', 'entidad__nombre', 'origen__nombre', 'destino__nombre')
    readonly_fields = ('creado', 'actualizado')

@admin.register(Pasajero)
class PasajeroAdmin(admin.ModelAdmin):
    list_display = ('id', 'viaje', 'nombre_completo', 'ci', 'telefono_contacto', 'confirmado', 'reservado_en')
    list_filter = ('viaje__entidad', 'confirmado')
    search_fields = ('nombre_completo', 'ci', 'telefono_contacto')

@admin.register(Puntuacion)
class PuntuacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'viaje', 'ci_cliente', 'categoria', 'valor', 'creado')
    list_filter = ('viaje__entidad', 'categoria', 'valor')
    search_fields = ('ci_cliente',)

@admin.register(LiquidacionMensual)
class LiquidacionMensualAdmin(admin.ModelAdmin):
    list_display = ('id', 'entidad', 'año', 'mes', 'ingresos_totales', 'comision', 'total_pasajeros', 'total_viajes', 'pagada')
    list_filter = ('entidad', 'año', 'mes', 'pagada')
    search_fields = ('entidad__nombre',)

@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'viaje', 'estado_anterior', 'estado_nuevo', 'fecha_cambio', 'usuario')
    list_filter = ('estado_anterior', 'estado_nuevo')
    search_fields = ('viaje__numero_viaje',)

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'tipo', 'viaje', 'leida', 'fecha_envio')
    list_filter = ('tipo', 'leida')
    search_fields = ('usuario__username', 'mensaje')

@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ('id', 'clave', 'valor', 'tipo_dato', 'descripcion')
    search_fields = ('clave',)