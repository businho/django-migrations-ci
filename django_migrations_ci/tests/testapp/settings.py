import importlib
import os

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECRET_KEY = "django-seriously-insecure"

DEBUG = True

INSTALLED_APPS = [
    "django_migrations_ci.tests.testapp",
    "django_migrations_ci",
]

_DATABASES_MODULE = os.getenv("DATABASES_MODULE", "sqlite")
DATABASES_MODULE = f"django_migrations_ci.tests.testapp.settings_{_DATABASES_MODULE}"
DATABASES = importlib.import_module(DATABASES_MODULE).DATABASES
