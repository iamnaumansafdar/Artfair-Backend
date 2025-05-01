#!/bin/sh
echo "Starting Celery worker..."
celery -A conf worker --loglevel=info
