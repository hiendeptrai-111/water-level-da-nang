from django.contrib.postgres.fields import ArrayField
from django.db import models


class Ward(models.Model):
    """Commune-level administrative unit of Da Nang (Resolution 1659/NQ-UBTVQH15)."""

    class Kind(models.TextChoices):
        WARD = "ward", "Phường"
        COMMUNE = "commune", "Xã"
        SPECIAL_ZONE = "special_zone", "Đặc khu"

    name = models.CharField("tên", max_length=100)
    kind = models.CharField("loại", max_length=20, choices=Kind.choices)
    latitude = models.DecimalField("vĩ độ", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("kinh độ", max_digits=9, decimal_places=6, null=True, blank=True)
    # Lower = shown first in the select box (downstream communes from Appendix B first).
    priority = models.PositiveSmallIntegerField("thứ tự ưu tiên", default=100)

    class Meta:
        verbose_name = "phường/xã"
        verbose_name_plural = "phường/xã"
        ordering = ["priority", "name"]
        constraints = [models.UniqueConstraint(fields=["kind", "name"], name="uniq_ward_kind_name")]

    def __str__(self):
        return f"{self.get_kind_display()} {self.name}"


class RescueTeam(models.Model):
    """Minimal rescue team (the rest is done in phase 4)."""

    class Vehicle(models.TextChoices):
        RESCUE_TRUCK = "rescue_truck", "Xe cứu hộ"
        MOTORBIKE = "motorbike", "Xe máy"
        BOAT = "boat", "Ca nô"

    name = models.CharField("tên đội", max_length=150, unique=True)
    phone_number = models.CharField("số điện thoại", max_length=15)
    vehicles = ArrayField(
        models.CharField(max_length=20, choices=Vehicle.choices),
        verbose_name="phương tiện", default=list, blank=True,
    )

    class Meta:
        verbose_name = "đội cứu hộ"
        verbose_name_plural = "đội cứu hộ"
        ordering = ["name"]

    def __str__(self):
        return self.name
