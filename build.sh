#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements/production.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Create superuser if environment variables are set
if [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    export DJANGO_SUPERUSER_FULL_NAME=${DJANGO_SUPERUSER_FULL_NAME:-"Admin User"}
    export DJANGO_SUPERUSER_PHONE=${DJANGO_SUPERUSER_PHONE:-"0000000000"}
    
    python manage.py createsuperuser \
        --no-input \
        --email $DJANGO_SUPERUSER_EMAIL || true
fi
