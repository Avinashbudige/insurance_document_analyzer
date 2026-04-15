#!/bin/bash
set -e

echo "Starting Django Document Analyzer..."

# Wait for database
echo "Waiting for database..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "Database is ready!"

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z $REDIS_HOST $REDIS_PORT; do
  sleep 0.1
done
echo "Redis is ready!"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if needed
echo "Creating superuser..."
python manage.py shell << EOF
from django.contrib.auth.models import User
import os

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser {username} created')
else:
    print(f'Superuser {username} already exists')
EOF

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn document_analyzer.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class gevent \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile /app/logs/access.log \
    --error-logfile /app/logs/error.log \
    --log-level info