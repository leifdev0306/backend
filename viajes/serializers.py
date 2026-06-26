from rest_framework import serializers
from .models import (
    Provincia, Entidad, Conductor, Vehiculo, Ruta, Viaje,
    Reserva, Puntuacion, Notificacion, LiquidacionMensual,
    Configuracion, Promocion
)
from django.contrib.auth.models import User

# ---------- Serializers básicos ----------
class ProvinciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provincia
        fields = '__all__'

class EntidadSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    class Meta:
        model = Entidad
        fields = ['id', 'username', 'email', 'nombre', 'provincia', 'direccion', 'telefono', 'is_active', 'fecha_registro']

class ConductorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conductor
        fields = '__all__'

class VehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehiculo
        fields = '__all__'

class RutaSerializer(serializers.ModelSerializer):
    origen_nombre = serializers.CharField(source='origen.nombre', read_only=True)
    destino_nombre = serializers.CharField(source='destino.nombre', read_only=True)
    class Meta:
        model = Ruta
        fields = ['id', 'origen', 'destino', 'origen_nombre', 'destino_nombre', 'distancia_km', 'duracion_estimada', 'activa']

class ViajeSerializer(serializers.ModelSerializer):
    entidad_nombre = serializers.CharField(source='entidad.nombre', read_only=True)
    ruta_detalle = RutaSerializer(source='ruta', read_only=True)
    reservas_count = serializers.IntegerField(source='reservas.count', read_only=True)
    puntuacion_promedio = serializers.SerializerMethodField()

    class Meta:
        model = Viaje
        fields = [
            'id', 'entidad', 'entidad_nombre', 'ruta', 'ruta_detalle',
            'conductor', 'vehiculo', 'fecha_salida', 'fecha_llegada_estimada',
            'precio', 'asientos_totales', 'asientos_disponibles', 'estado',
            'descripcion', 'imagen_url', 'created_at', 'updated_at',
            'reservas_count', 'puntuacion_promedio'
        ]
        read_only_fields = ['entidad', 'created_at', 'updated_at']

    def get_puntuacion_promedio(self, obj):
        avg = obj.puntuaciones.aggregate(models.Avg('puntuacion'))['puntuacion__avg']
        return round(avg, 1) if avg else None

class ReservaSerializer(serializers.ModelSerializer):
    viaje_detalle = ViajeSerializer(source='viaje', read_only=True)
    class Meta:
        model = Reserva
        fields = [
            'id', 'viaje', 'viaje_detalle', 'nombre_cliente', 'carnet_cliente',
            'telefono', 'email', 'asientos_reservados', 'estado',
            'token_cancelacion', 'created_at', 'updated_at'
        ]
        read_only_fields = ['viaje', 'estado', 'token_cancelacion']

class PuntuacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Puntuacion
        fields = '__all__'
        read_only_fields = ['fecha']

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = '__all__'
        read_only_fields = ['fecha_envio']

class LiquidacionMensualSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiquidacionMensual
        fields = '__all__'
        read_only_fields = ['fecha_calculo']

class ConfiguracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuracion
        fields = '__all__'

class PromocionSerializer(serializers.ModelSerializer):
    entidad_nombre = serializers.CharField(source='entidad.nombre', read_only=True)
    viaje_detalle = ViajeSerializer(source='viaje', read_only=True)
    class Meta:
        model = Promocion
        fields = '__all__'