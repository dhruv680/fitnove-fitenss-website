"""
WSGI config for fitnova project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fitnova.settings')

application = get_wsgi_application()

# Startup Auto-Migrate Safeguard:
# Ensures all tables (accounts_user, etc.) are automatically migrated and seeded
# upon container start in ephemeral or newly provisioned environments (Render, Cloud, Docker).
try:
    from django.db import connection
    from django.core.management import call_command
    with connection.cursor() as cursor:
        existing_tables = connection.introspection.table_names(cursor)
        if 'accounts_user' not in existing_tables:
            print("==> FitNova Startup: Database tables missing (accounts_user). Running auto-migrations...")
            call_command('migrate', interactive=False)
            try:
                call_command('seed_fitnova', interactive=False)
            except Exception as e:
                print(f"==> Seed notice: {e}")
            print("==> Database auto-migration completed successfully!")
except Exception as e:
    print(f"==> Startup database check notice: {e}")
