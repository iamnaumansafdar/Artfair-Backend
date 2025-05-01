#!/bin/sh
# Run database migrations
python manage.py migrate --noinput

# Collect static files (if needed)
python manage.py collectstatic --noinput


# Start Gunicorn with environment variables
exec gunicorn conf.wsgi:application --bind 0.0.0.0:$PORT