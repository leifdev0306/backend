from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal

class Provincia(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Entidad(models.Model):
    PLANES = [
        ('basico', 'Básico'),
        ('premium', 'Premium'),
        ('empresarial', 'Empresarial'),
    ]
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True)
    descripcion = models.TextField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True, null=True)
    imagen_promocional = models.ImageField(upload_to='entidades/', blank=True, null=True)
    horario_atencion = models.CharField(max_length=200, blank=True)
    numero_licencia = models.CharField(max_length=50, blank=True)
    comision_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    suspendida = models.BooleanField(default=False)  # mantengo compatibilidad
    activa = models.BooleanField(default=True)
    plan = models.CharField(max_length=20, choices=PLANES, default='basico')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    puntuacion_promedio = models.FloatField(default=0.0)

    def recalcular_puntuacion(self):
        from .models import Puntuacion
        puntuaciones = Puntuacion.objects.filter(viaje__entidad=self, valor__isnull=False)
        if puntuaciones.exists():
            promedio = puntuaciones.aggregate(models.Avg('valor'))['valor__avg']
            self.puntuacion_promedio = round(promedio, 1)
        else:
            self.puntuacion_promedio = 0.0
        self.save(update_fields=['puntuacion_promedio'])

    def __str__(self):
        return self.nombre

class Gestor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='gestores')
    telefono = models.CharField(max_length=20, blank=True)
    notificaciones_email = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.entidad.nombre}"

class Conductor(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='conductores')
    nombre = models.CharField(max_length=200)
    cedula = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    licencia = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.cedula})"

class Vehiculo(models.Model):
    TIPOS = [
        ('avion', 'Avión'),
        ('tren', 'Tren'),
        ('omnibus', 'Ómnibus'),
        ('auto', 'Auto'),
        ('camion', 'Camión'),
        ('taxi', 'Taxi'),
        ('microbus', 'Microbús'),
    ]
    ESTADOS = [
        ('disponible', 'Disponible'),
        ('mantenimiento', 'Mantenimiento'),
        ('retirado', 'Retirado'),
    ]
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='vehiculos')
    placa = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    modelo = models.CharField(max_length=100, blank=True)
    año = models.PositiveIntegerField(null=True, blank=True)
    capacidad = models.PositiveSmallIntegerField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='disponible')
    imagen_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.placa} - {self.get_tipo_display()}"

class Ruta(models.Model):
    origen = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name='rutas_origen')
    destino = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name='rutas_destino')
    distancia_km = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tiempo_estimado_min = models.PositiveIntegerField(default=60)
    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ['origen', 'destino']

    def __str__(self):
        return f"{self.origen} → {self.destino}"

class Viaje(models.Model):
    TIPO_VEHICULO = [
        ('avion','Avión'),
        ('tren','Tren'),
        ('omnibus','Ómnibus'),
        ('auto','Auto'),
        ('camion','Camión'),
        ('taxi','Taxi'),
        ('microbus','Microbús'),
    ]
    ESTADO_CHOICES = [
        ('activo','Activo'),
        ('lleno','Lleno'),
        ('en_curso','En curso'),
        ('completado','Completado'),
        ('cancelado','Cancelado'),
        ('cancelado_tarde', 'Cancelado tarde'),  # cancelado sin tiempo suficiente
    ]
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='viajes')
    conductor = models.ForeignKey(Conductor, on_delete=models.SET_NULL, null=True, blank=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.SET_NULL, null=True, blank=True)
    ruta = models.ForeignKey(Ruta, on_delete=models.SET_NULL, null=True, blank=True)
    origen = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name='viajes_origen')
    destino = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name='viajes_destino')
    lugar_salida = models.CharField(max_length=255)
    lugar_llegada = models.CharField(max_length=255)
    fecha = models.DateField(db_index=True)
    hora = models.TimeField()
    tipo_vehiculo = models.CharField(max_length=20, choices=TIPO_VEHICULO)
    matricula = models.CharField(max_length=20)
    capacidad = models.PositiveSmallIntegerField()
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo', db_index=True)
    numero_viaje = models.CharField(max_length=20, blank=True)
    duracion_estimada = models.PositiveIntegerField(help_text="Duración en minutos", default=60)
    kilometraje = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notas_internas = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['entidad', 'estado']),
            models.Index(fields=['fecha', 'estado']),
        ]

    @property
    def pasajeros_count(self):
        return self.reservas.count()

    @property
    def cupos_disponibles(self):
        return self.capacidad - self.pasajeros_count

    @property
    def fecha_hora_salida(self):
        return timezone.make_aware(
            datetime.combine(self.fecha, self.hora)
        ) if timezone.is_naive else datetime.combine(self.fecha, self.hora)

    def __str__(self):
        return f"{self.origen} → {self.destino} ({self.fecha} {self.hora})"

class Pasajero(models.Model):
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='reservas')
    nombre_completo = models.CharField(max_length=200)
    ci = models.CharField(max_length=20, db_index=True)
    telefono_contacto = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True)
    asiento_asignado = models.CharField(max_length=10, blank=True)
    confirmado = models.BooleanField(default=True)
    reservado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['viaje', 'ci']]

    def __str__(self):
        return f"{self.nombre_completo} - {self.ci}"

class Puntuacion(models.Model):
    CATEGORIAS = [
        ('servicio', 'Servicio'),
        ('puntualidad', 'Puntualidad'),
        ('vehiculo', 'Vehículo'),
        ('limpieza', 'Limpieza'),
        ('general', 'General'),
    ]
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='puntuaciones')
    ci_cliente = models.CharField(max_length=20, db_index=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default='general')
    valor = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        null=True,
        blank=True
    )
    comentario = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['viaje', 'ci_cliente', 'categoria']]

class LiquidacionMensual(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='liquidaciones')
    año = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    ingresos_totales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comision = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_pasajeros = models.PositiveIntegerField(default=0)
    total_viajes = models.PositiveIntegerField(default=0)
    pagada = models.BooleanField(default=False)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [['entidad', 'año', 'mes']]

    def __str__(self):
        return f"{self.entidad.nombre} - {self.mes}/{self.año}"

class HistorialEstado(models.Model):
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='historial_estados')
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    motivo = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.viaje} - {self.estado_anterior} → {self.estado_nuevo}"

class Notificacion(models.Model):
    TIPOS = [
        ('cambio_estado', 'Cambio de estado'),
        ('recordatorio', 'Recordatorio'),
        ('cancelacion', 'Cancelación'),
        ('promocion', 'Promoción'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    datos_extra = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.usuario.username}"

class Configuracion(models.Model):
    TIPO_DATO = [
        ('string', 'String'),
        ('int', 'Entero'),
        ('float', 'Decimal'),
        ('bool', 'Booleano'),
        ('json', 'JSON'),
    ]
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descripcion = models.CharField(max_length=255, blank=True)
    tipo_dato = models.CharField(max_length=10, choices=TIPO_DATO, default='string')

    def __str__(self):
        return f"{self.clave} = {self.valor}"