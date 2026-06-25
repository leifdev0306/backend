from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import (
    Provincia, Entidad, Viaje, Pasajero, Gestor, Conductor, Vehiculo,
    Ruta, Puntuacion, LiquidacionMensual, HistorialEstado, Notificacion,
    Configuracion
)
from decimal import Decimal

class ProvinciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provincia
        fields = '__all__'

class EntidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entidad
        fields = '__all__'
        read_only_fields = ['puntuacion_promedio', 'fecha_registro']

class ConductorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conductor
        fields = '__all__'

class VehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehiculo
        fields = '__all__'

class RutaSerializer(serializers.ModelSerializer):
    origen_nombre = serializers.ReadOnlyField(source='origen.nombre')
    destino_nombre = serializers.ReadOnlyField(source='destino.nombre')

    class Meta:
        model = Ruta
        fields = '__all__'

class ViajeSerializer(serializers.ModelSerializer):
    origen_nombre = serializers.ReadOnlyField(source='origen.nombre')
    destino_nombre = serializers.ReadOnlyField(source='destino.nombre')
    cupos_disponibles = serializers.ReadOnlyField()
    pasajeros_count = serializers.ReadOnlyField()
    entidad_nombre = serializers.ReadOnlyField(source='entidad.nombre')
    entidad_puntuacion = serializers.SerializerMethodField()
    entidad_imagen_promocional = serializers.SerializerMethodField()
    conductor_nombre = serializers.ReadOnlyField(source='conductor.nombre', default=None)
    vehiculo_placa = serializers.ReadOnlyField(source='vehiculo.placa', default=None)
    ruta_info = serializers.SerializerMethodField()

    class Meta:
        model = Viaje
        fields = '__all__'
        read_only_fields = ['estado', 'creado', 'actualizado', 'entidad', 'numero_viaje']

    def get_entidad_puntuacion(self, obj):
        return obj.entidad.puntuacion_promedio

    def get_entidad_imagen_promocional(self, obj):
        if obj.entidad.imagen_promocional:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.entidad.imagen_promocional.url)
            return obj.entidad.imagen_promocional.url
        return None

    def get_ruta_info(self, obj):
        if obj.ruta:
            return {
                'id': obj.ruta.id,
                'distancia_km': obj.ruta.distancia_km,
                'tiempo_estimado_min': obj.ruta.tiempo_estimado_min,
            }
        return None

    def validate(self, data):
        # Validar que fecha/hora no sea pasada (excepto para actualizaciones)
        if self.instance is None:
            fecha = data.get('fecha')
            hora = data.get('hora')
            if fecha and hora:
                from datetime import datetime
                now = datetime.now()
                salida = datetime.combine(fecha, hora)
                if salida < now:
                    raise serializers.ValidationError("La fecha/hora de salida no puede ser pasada.")
        return data

class PasajeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pasajero
        fields = ['id', 'viaje', 'nombre_completo', 'ci', 'telefono_contacto',
                  'email', 'asiento_asignado', 'confirmado', 'reservado_en']

class PuntuacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Puntuacion
        fields = ['id', 'viaje', 'ci_cliente', 'categoria', 'valor', 'comentario', 'creado']

    def validate(self, data):
        viaje = data.get('viaje')
        ci = data.get('ci_cliente')
        if viaje and ci and Puntuacion.objects.filter(viaje=viaje, ci_cliente=ci, categoria=data.get('categoria')).exists():
            raise serializers.ValidationError("Ya has puntuado este viaje en esta categoría.")
        return data

class LiquidacionMensualSerializer(serializers.ModelSerializer):
    entidad_nombre = serializers.ReadOnlyField(source='entidad.nombre')

    class Meta:
        model = LiquidacionMensual
        fields = '__all__'
        read_only_fields = ['ingresos_totales', 'comision', 'total_pasajeros', 'total_viajes', 'fecha_cierre']

class HistorialEstadoSerializer(serializers.ModelSerializer):
    usuario_username = serializers.ReadOnlyField(source='usuario.username', default=None)

    class Meta:
        model = HistorialEstado
        fields = ['id', 'viaje', 'estado_anterior', 'estado_nuevo', 'fecha_cambio', 'usuario_username', 'motivo']

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ['id', 'usuario', 'viaje', 'tipo', 'mensaje', 'leida', 'fecha_envio', 'datos_extra']

class ConfiguracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuracion
        fields = '__all__'

class GestorSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    entidad_nombre = serializers.ReadOnlyField(source='entidad.nombre')

    class Meta:
        model = Gestor
        fields = ['id', 'entidad', 'entidad_nombre', 'username', 'password', 'telefono', 'notificaciones_email']

    def create(self, validated_data):
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        user = User.objects.create_user(username=username, password=password)
        return Gestor.objects.create(user=user, **validated_data)