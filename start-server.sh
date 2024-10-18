#!/bin/sh

echo "Running start-server.sh"
# Run database migrations
python manage.py makemigrations
python manage.py migrate
python manage.py insert_objectives

# Check if the superuser is already created
if [ ! -f /usr/src/app/.superuser_created ]; then
    # Create superuser
    python manage.py create_superuser_if_not_exists --email "vincent_gomez@hotmail.com" --password "Ben071241"

    # Mark the setup as done
    touch /usr/src/app/.superuser_created
fi

# Start the application server
gunicorn --workers 3 --bind 0.0.0.0:8080 backend_v2.wsgi:application
