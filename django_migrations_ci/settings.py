from django.conf import settings

storage_class = getattr(
    settings,
    "MIGRATECI_STORAGE",
    "django.core.files.storage.FileSystemStorage",
)
location = getattr(settings, "MIGRATECI_LOCATION", "")
depth = getattr(settings, "MIGRATECI_DEPTH", 0)
is_pytest = getattr(settings, "MIGRATECI_PYTEST", False)
parallel = getattr(settings, "MIGRATECI_PARALLEL", None)
