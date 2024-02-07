from django.db import models


class Bus(models.Model):
    plate = models.TextField()  # type: ignore[var-annotated]
