#!/bin/bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn visitor_management.wsgi:application --bind=0.0.0.0:8000
