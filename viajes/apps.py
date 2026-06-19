from django.apps import AppConfig
import os

class ViajesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'viajes'

    def ready(self):
        if os.environ.get('RENDER'):
            try:
                from django.core.management import call_command
                print("Generando migraciones para viajes...")
                call_command('makemigrations', 'viajes', interactive=False)
                print("Ejecutando migraciones pendientes...")
                call_command('migrate', interactive=False)

                from django.contrib.auth import get_user_model
                User = get_user_model()
                if not User.objects.filter(is_superuser=True).exists():
                    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
                    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
                    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
                    print(f"Creando superusuario: {username}")
                    User.objects.create_superuser(username, email, password)
            except Exception as e:
                print(f"Error: {e}")