from django.core.management.base import BaseCommand
from viajes.models import Viaje
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Elimina viajes completados o cancelados con más de 24h después de la salida'

    def handle(self, *args, **options):
        ahora = datetime.now()
        limite = ahora - timedelta(hours=24)
        viajes_a_borrar = Viaje.objects.filter(
            fecha__lt=limite.date()
        ) | Viaje.objects.filter(
            fecha=limite.date(), hora__lt=limite.time()
        )
        count = viajes_a_borrar.count()
        viajes_a_borrar.delete()
        self.stdout.write(f"Se eliminaron {count} viajes antiguos")