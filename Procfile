web: python manage.py migrate --no-input && python manage.py seed_fitnova && gunicorn fitnova.wsgi:application --bind 0.0.0.0:$PORT
