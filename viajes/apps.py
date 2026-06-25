from django.apps import AppConfig
import os
import sys

class ViajesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'viajes'

    def ready(self):
        if os.environ.get('RENDER'):
            try:
                from django.db import connection, transaction
                from django.core.management import call_command

                print("🔧 Verificando y actualizando esquema de base de datos...")

                with connection.cursor() as cursor:
                    # Obtener columnas actuales de la tabla viajes_entidad
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'viajes_entidad'
                    """)
                    existing_columns = [row[0] for row in cursor.fetchall()]

                    # Definir columnas que deberían existir (modelo Entidad)
                    required_columns = {
                        'email': 'varchar(254)',
                        'direccion': 'text',
                        'descripcion': 'text',
                        'logo_url': 'varchar(500)',
                        'horario_atencion': 'varchar(200)',
                        'numero_licencia': 'varchar(50)',
                        'activa': 'boolean DEFAULT true',
                        'plan': 'varchar(20) DEFAULT \'basico\'',
                        'fecha_registro': 'timestamp with time zone DEFAULT now()',
                        # Nota: imagen_promocional ya debería existir, pero si no, se añade también
                        'imagen_promocional': 'varchar(100)',
                    }

                    # Verificar y añadir columnas faltantes
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

                    # Verificar si existen otras tablas nuevas (Conductor, Vehiculo, etc.)
                    # Pero por ahora, con las migraciones posteriores se crearán.

                # Ahora ejecutar migraciones pendientes para el resto de modelos
                print("🔧 Ejecutando migraciones pendientes...")
                call_command('migrate', interactive=False)
                print("✅ Migraciones ejecutadas.")

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
        else:
            # En entornos locales, puedes mantener la lógica de migración normal
            pass