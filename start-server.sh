#!/bin/sh


echo "Running start-server.sh"


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
gunicorn --workers 3 --bind 0.0.0.0:8080 backend_v2.wsgi:application