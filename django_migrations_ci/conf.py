from django.conf import settings as django_settings
from django.utils.functional import SimpleLazyObject


def _setting(setting, default=None):
    return getattr(django_settings, setting, default)


class Settings:
    def __init__(self):
        self.location = _setting("MIGRATECI_LOCATION", "")
        self.depth = _setting("MIGRATECI_DEPTH", 1)
        self.is_pytest = _setting("MIGRATECI_PYTEST", False)
        self.parallel = _setting("MIGRATECI_PARALLEL", None)

        self.storage_class = _setting(
            "MIGRATECI_STORAGE",
            "django.core.files.storage.FileSystemStorage",
        )


settings = SimpleLazyObject(Settings)
