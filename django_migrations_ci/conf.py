from pathlib import Path

from django.conf import settings as django_settings
from django.utils.functional import SimpleLazyObject


def _setting(setting, default=None):
    return getattr(django_settings, setting, default)


class Settings:
    def __init__(self):
        self.location = _setting("MIGRATECI_LOCATION", "")
        self.depth = _setting("MIGRATECI_DEPTH", 0)
        self.is_pytest = _setting("MIGRATECI_PYTEST", False)
        self.parallel = _setting("MIGRATECI_PARALLEL", None)

        self.storage_class = _setting("MIGRATECI_STORAGE")
        if self.storage_class is None:
            self.storage_class = "django.core.files.storage.FileSystemStorage"
            if not self.location:
                self.location = Path("~/.migrateci")
                self.location.expanduser().mkdir(parents=True, exist_ok=True)


settings = SimpleLazyObject(Settings)
