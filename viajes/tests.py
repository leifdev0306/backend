from django.test import TestCase
from django.contrib.auth.models import User
from .models import *
from .services import ReservaService

class ViajeTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='test', password='test')
        self.entidad = Entidad.objects.create(user=user, nombre='Test Agency')
        provincia = Provincia.objects.create(nombre='La Habana')
        ruta = Ruta.objects.create(origen=provincia, destino=provincia, distancia_km=100, duracion_estimada='02:00:00')
        self.viaje = Viaje.objects.create(
            entidad=self.entidad,
            ruta=ruta,
            fecha_salida='2026-07-01 08:00:00',
            fecha_llegada_estimada='2026-07-01 10:00:00',
            precio=50,
            asientos_totales=10,
            asientos_disponibles=10
        )

    def test_reserva(self):
        data = {'nombre_cliente': 'Juan', 'carnet_cliente': '123', 'asientos_reservados': 2}
        reserva = ReservaService.crear_reserva(self.viaje.id, data)
        self.assertEqual(reserva.asientos_reservados, 2)
        self.viaje.refresh_from_db()
        self.assertEqual(self.viaje.asientos_disponibles, 8)