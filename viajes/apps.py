from django.apps import AppConfig
import os

class ViajesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'viajes'

    def ready(self):
        if os.environ.get('RENDER'):
            try:
                from django.db import connection
                from django.contrib.auth import get_user_model

                # Verificar y crear columna imagen_promocional si no existe
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                           WHERE table_name='viajes_entidad' AND column_name='imagen_promocional') THEN
                                ALTER TABLE viajes_entidad ADD COLUMN imagen_promocional varchar(500);
                            END IF;
                        END $$;
                    """)
                    print("✅ Columna imagen_promocional verificada/creada")

                # Crear superusuario si no existe
                User = get_user_model()
                if not User.objects.filter(is_superuser=True).exists():
                    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
                    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
                    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
                    print(f"🔧 Creando superusuario: {username}")
                    User.objects.create_superuser(username, email, password)

            except Exception as e:
                print(f"⚠️ Error en migración automática: {e}")