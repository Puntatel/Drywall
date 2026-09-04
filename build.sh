#!/usr/bin/env bash
# Salir inmediatamente si algún comando falla
set -o errexit

# 1. Instalar las dependencias de Python
pip install -r requirements.txt

# 2. Ejecutar las migraciones de forma automática en la base de datos de internet
python manage.py migrate

# 3. Crear el administrador inicial de forma automática si no existe
# Usamos variables de entorno para que Render inyecte la contraseña de forma segura
python manage.py createsuperuser --noinput || true
