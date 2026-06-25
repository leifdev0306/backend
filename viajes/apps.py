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

                print("🔧 Verificando y actualizando esquema de base de datos...")

                # Verificar si las tablas principales existen
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) FROM information_schema.tables
                        WHERE table_name = 'viajes_entidad'
                    """)
                    table_exists = cursor.fetchone()[0] > 0

                if not table_exists:
                    print("🔧 Creando tablas desde cero...")
                    call_command('makemigrations', 'viajes', interactive=False)
                    call_command('migrate', interactive=False)
                else:
                    # Verificar columnas faltantes en Entidad
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'viajes_entidad'
                    """)
                    existing_columns = [row[0] for row in cursor.fetchall()]

                    required_columns = {
                        'email': 'varchar(254)',
                        'direccion': 'text',
                        'descripcion': 'text',
                        'logo': 'varchar(100)',
                        'imagen_promocional': 'varchar(100)',
                        'horario_atencion': 'varchar(200)',
                        'numero_licencia': 'varchar(50)',
                        'activa': 'boolean DEFAULT true',
                        'plan': 'varchar(20) DEFAULT \'basico\'',
                        'fecha_registro': 'timestamp with time zone DEFAULT now()',
                    }

                    for col, col_type in required_columns.items():
                        if col not in existing_columns:
                            print(f"🔧 Añadiendo columna '{col}' a viajes_entidad...")
                            try:
                                cursor.execute(f"""
                                    ALTER TABLE viajes_entidad
                                    ADD COLUMN {col} {col_type};
                                """)
                                print(f"✅ Columna '{col}' añadida.")
                            except Exception as e:
                                print(f"⚠️ Error añadiendo columna '{col}': {e}")

                    # Ejecutar migraciones para el resto de modelos
                    call_command('migrate', interactive=False)

                # Crear superusuario
                from django.contrib.auth import get_user_model
                User = get_user_model()
                if not User.objects.filter(is_superuser=True).exists():
                    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
                    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
                    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
                    print(f"🔧 Creando superusuario: {username}")
                    User.objects.create_superuser(username, email, password)

                print("✅ Inicialización completada.")

            except Exception as e:
                print(f"⚠️ Error en migración automática: {e}")