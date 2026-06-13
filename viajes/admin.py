from django.contrib import admin
from .models import Entidad, Gestor, Viaje, Pasajero, LiquidacionMensual

@admin.register(Entidad)
class EntidadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'telefono', 'comision_porcentaje', 'suspendida']
    list_editable = ['suspendida']

@admin.register(Gestor)
class GestorAdmin(admin.ModelAdmin):
    list_display = ['user', 'entidad']

@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ['id', 'entidad', 'origen', 'destino', 'fecha', 'hora', 'estado', 'cupos_disponibles']
    list_filter = ['estado', 'entidad']

@admin.register(Pasajero)
class PasajeroAdmin(admin.ModelAdmin):
    list_display = ['viaje', 'nombre_completo', 'ci', 'reservado_en']

@admin.register(LiquidacionMensual)
class LiquidacionAdmin(admin.ModelAdmin):
    list_display = ['entidad', 'año', 'mes', 'ingresos_totales', 'comision', 'pagada']
    list_editable = ['pagada']