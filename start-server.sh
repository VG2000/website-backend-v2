#!/bin/sh
set -e  # Exit immediately if a command exits with a non-zero status

echo "Running start-server.sh"

nslookup website-db-v2.cruuok6w6x96.eu-west-2.rds.amazonaws.com
telnet website-db-v2.cruuok6w6x96.eu-west-2.rds.amazonaws.com 5432

# Run database migrations
python manage.py makemigrations
python manage.py migrate
python manage.py insert_geography
python manage.py insert_objectives
python manage.py insert_books_and_currencies
python manage.py create_projects_if_not_exists
python manage.py insert_objectives

# Check if the superuser is already created
if [ ! -f /usr/src/app/.superuser_created ]; then
    # Create superuser if not exists
    python manage.py create_superuser_if_not_exists --superuser_email "vincent_gomez@hotmail.com" --superuser_password "Ben071241"

    # Mark the setup as done
    touch /usr/src/app/.superuser_created
fi

# Start the application server
exec gunicorn --workers 3 --bind 0.0.0.0:8080 backend_v2.wsgi:application --timeout 120