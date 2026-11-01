"""Kept for old instructions: use `python manage.py seed_demo` instead."""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.core.management import call_command  # noqa: E402

if __name__ == '__main__':
    call_command('seed_demo')
