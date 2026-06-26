from django.apps import AppConfig
from django.core.management import call_command
from django.db.utils import OperationalError, ProgrammingError
import sys
import os

class ViajesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'viajes'

    def ready(self):
        if os.environ.get('RUN_MAIN') or os.environ.get('DJANGO_AUTORELOAD'):
            return
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
        if 'test' in sys.argv:
            return

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            call_command('migrate', verbosity=0)
        except (OperationalError, ProgrammingError) as e:
            print(f"Error al migrar: {e}")

        try:
            if not User.objects.filter(username='leifdev').exists():
                User.objects.create_superuser(
                    username='leifdev',
                    email='leifdev0306@gmail.com',
                    password='Palas@123'
                )
                print("Superusuario 'leifdev' creado con éxito.")
            else:
                print("Superusuario 'leifdev' ya existe.")
        except Exception as e:
            print(f"Error al crear superusuario: {e}")