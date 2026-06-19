import os
import sys
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Ejecutar migraciones y crear superusuario al inicio
try:
    from django.db import connections
    from django.db.utils import OperationalError
    # Verificar si la base de datos está accesible
    db_conn = connections['default']
    db_conn.cursor()
except OperationalError:
    pass  # Si falla, no hacemos nada (la base de datos podría no estar lista)
else:
    # Ejecutar migraciones
    print("Ejecutando migraciones pendientes...")
    call_command('migrate', interactive=False)

    # Crear superusuario si no existe
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(is_superuser=True).exists():
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
        print(f"Creando superusuario: {username}")
        User.objects.create_superuser(username, email, password)

application = get_wsgi_application()