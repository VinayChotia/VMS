#!/bin/bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
python manage.py shell <<EOF
from account.models import Employee
if not Employee.objects.filter(email='admin@vms.com').exists():
    Employee.objects.create_superuser(email='admin@vms.com', password='adminpassword123', full_name='System Admin')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
EOF

gunicorn visitor_management.wsgi:application --bind=0.0.0.0:8000
