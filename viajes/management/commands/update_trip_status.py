from django.core.management.base import BaseCommand
from viajes.models import Viaje
from datetime import datetime

class Command(BaseCommand):
    help = 'Actualiza estados de viajes (activo -> en_curso)'

    def handle(self, *args, **options):
        ahora = datetime.now()
        viajes = Viaje.objects.filter(estado='activo', fecha__lte=ahora.date())
        for v in viajes:
            salida = datetime.combine(v.fecha, v.hora)
            if salida <= ahora:
                v.estado = 'en_curso'
                v.save()
        self.stdout.write("Estados actualizados")