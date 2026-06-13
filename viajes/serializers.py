from rest_framework import serializers
from .models import Provincia, Entidad, Viaje, Pasajero, Gestor, LiquidacionMensual
from django.contrib.auth.models import User

class ProvinciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provincia
        fields = '__all__'

class EntidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entidad
        fields = ['id', 'nombre', 'telefono', 'comision_porcentaje', 'suspendida']

class ViajeSerializer(serializers.ModelSerializer):
    origen_nombre = serializers.ReadOnlyField(source='origen.nombre')
    destino_nombre = serializers.ReadOnlyField(source='destino.nombre')
    cupos_disponibles = serializers.ReadOnlyField()
    pasajeros_count = serializers.ReadOnlyField()
    entidad_nombre = serializers.ReadOnlyField(source='entidad.nombre')

    class Meta:
        model = Viaje
        fields = '__all__'
        read_only_fields = ['estado', 'creado']

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
        gestor = Gestor.objects.create(user=user, **validated_data)
        return gestor

class LiquidacionMensualSerializer(serializers.ModelSerializer):
    entidad_nombre = serializers.ReadOnlyField(source='entidad.nombre')

    class Meta:
        model = LiquidacionMensual
        fields = '__all__'
        read_only_fields = ['ingresos_totales', 'comision']