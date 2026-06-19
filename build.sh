#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Crear directorio para archivos estáticos (si no existe)
mkdir -p staticfiles

# Recolectar archivos estáticos (incluye los del admin)
python manage.py collectstatic --noinput

python manage.py makemigrations
python manage.py migrate