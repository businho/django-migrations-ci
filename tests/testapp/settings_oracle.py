import os

_host = os.getenv("ORACLE_HOST", "localhost")
_port = os.getenv("ORACLE_PORT", "1521")
_service = os.getenv("ORACLE_SERVICE", "FREEPDB1")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.oracle",
        # Easy Connect string, because NAME is a SID when HOST and PORT are set.
        "NAME": f"{_host}:{_port}/{_service}",
        "USER": os.getenv("ORACLE_USER", "system"),
        "PASSWORD": os.getenv("ORACLE_PASSWORD", "oracle"),
    },
}
