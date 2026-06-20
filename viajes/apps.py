from django.apps import AppConfig
import os

class ViajesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'viajes'

    def ready(self):
        if os.environ.get('RENDER'):
            try:
                from django.core.management import call_command
                from django.db import connection

                # Verificar si la columna imagen_promocional existe
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name='viajes_entidad' AND column_name='imagen_promocional'
                    """)
                    exists = cursor.fetchone()

                if not exists:
                    print("🔧 Forzando creación de columna imagen_promocional...")
                    call_command('makemigrations', 'viajes', interactive=False)
                    call_command('migrate', interactive=False)
                    print("✅ Migración completada")

                # Crear superusuario si no existe
                from django.contrib.auth import get_user_model
                User = get_user_model()
                if not User.objects.filter(is_superuser=True).exists():
                    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
                    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
                    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
                    print(f"🔧 Creando superusuario: {username}")
                    User.objects.create_superuser(username, email, password)

            except Exception as e:
                print(f"⚠️ Error en migración automática: {e}")