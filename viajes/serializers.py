from rest_framework import serializers
from .models import Provincia, Entidad, Viaje, Pasajero, Gestor, LiquidacionMensual, Puntuacion
from django.contrib.auth.models import User

class ProvinciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provincia
        fields = '__all__'

class EntidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entidad
        fields = '__all__'

class ViajeSerializer(serializers.ModelSerializer):
    origen_nombre = serializers.ReadOnlyField(source='origen.nombre')
    destino_nombre = serializers.ReadOnlyField(source='destino.nombre')
    cupos_disponibles = serializers.ReadOnlyField()
    pasajeros_count = serializers.ReadOnlyField()
    entidad_nombre = serializers.ReadOnlyField(source='entidad.nombre')
    entidad_puntuacion = serializers.SerializerMethodField()
    entidad_imagen_promocional = serializers.SerializerMethodField()

    class Meta:
        model = Viaje
        fields = '__all__'
        read_only_fields = ['estado', 'creado', 'entidad']

    def get_entidad_puntuacion(self, obj):
        return obj.entidad.puntuacion_promedio

    def get_entidad_imagen_promocional(self, obj):
        if obj.entidad.imagen_promocional:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.entidad.imagen_promocional.url)
            return obj.entidad.imagen_promocional.url
        return None

class PasajeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pasajero
        fields = ['id', 'viaje', 'nombre_completo', 'ci', 'reservado_en']

class GestorSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Gestor
        fields = ['id', 'entidad', 'username', 'password']

    def create(self, validated_data):
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        user = User.objects.create_user(username=username, password=password)
        return Gestor.objects.create(user=user, **validated_data)

class LiquidacionMensualSerializer(serializers.ModelSerializer):
    entidad_nombre = serializers.ReadOnlyField(source='entidad.nombre')

    class Meta:
        model = LiquidacionMensual
        fields = '__all__'
        read_only_fields = ['ingresos_totales', 'comision', 'total_pasajeros', 'total_viajes_completados']

class PuntuacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Puntuacion
        fields = ['id', 'viaje', 'ci_cliente', 'valor', 'comentario', 'creado']