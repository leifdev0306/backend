from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date, datetime

class Provincia(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Entidad(models.Model):
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    comision_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    suspendida = models.BooleanField(default=False)  # para desactivar viajes si no paga
    creada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Gestor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='gestores')

    def __str__(self):
        return f"{self.user.username} - {self.entidad.nombre}"

class Viaje(models.Model):
    TIPO_VEHICULO = [
        ('avion', 'Avión'),
        ('tren', 'Tren'),
        ('omnibus', 'Ómnibus'),
        ('auto', 'Auto'),
        ('camion', 'Camión'),
    ]
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('lleno', 'Lleno'),
        ('en_curso', 'En curso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='viajes')
    origen = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name='viajes_origen')
    destino = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name='viajes_destino')
    lugar_salida = models.CharField(max_length=255)
    lugar_llegada = models.CharField(max_length=255)
    fecha = models.DateField()
    hora = models.TimeField()
    tipo_vehiculo = models.CharField(max_length=20, choices=TIPO_VEHICULO)
    matricula = models.CharField(max_length=20)
    capacidad = models.PositiveSmallIntegerField()
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    creado = models.DateTimeField(auto_now_add=True)

    @property
    def pasajeros_count(self):
        return self.reservas.count()

    @property
    def cupos_disponibles(self):
        return self.capacidad - self.pasajeros_count

    def actualizar_estado_automatico(self):
        ahora = datetime.now()
        salida = datetime.combine(self.fecha, self.hora)
        if self.estado == 'cancelado':
            return
        if self.estado == 'completado':
            return
        if salida <= ahora and self.estado != 'completado':
            self.estado = 'en_curso'
        elif self.cupos_disponibles <= 0 and self.estado == 'activo':
            self.estado = 'lleno'
        elif self.cupos_disponibles > 0 and self.estado == 'lleno' and salida > ahora:
            self.estado = 'activo'
        self.save(update_fields=['estado'])

    def __str__(self):
        return f"{self.origen} -> {self.destino} ({self.fecha} {self.hora})"

class Pasajero(models.Model):
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='reservas')
    nombre_completo = models.CharField(max_length=200)
    ci = models.CharField(max_length=20)
    reservado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['viaje', 'ci']]  # evitar doble reserva del mismo CI en mismo viaje

class LiquidacionMensual(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='liquidaciones')
    año = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()  # 1-12
    ingresos_totales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comision = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pagada = models.BooleanField(default=False)

    class Meta:
        unique_together = [['entidad', 'año', 'mes']]

    def calcular_comision(self):
        return self.ingresos_totales * (self.entidad.comision_porcentaje / 100)

    def save(self, *args, **kwargs):
        self.comision = self.calcular_comision()
        super().save(*args, **kwargs)