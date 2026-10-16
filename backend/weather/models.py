from django.db import models
from django.utils.timezone import localtime


class WeatherReading(models.Model):
    """Cache of Open-Meteo hourly weather at each commune centre (CN13, CN14).
    observed = hours up to the current hour (model values, past_days), forecast = later hours.
    precipitation is the total of the PRECEDING hour (Open-Meteo convention)."""

    class Kind(models.TextChoices):
        OBSERVED = "observed", "Đã qua"
        FORECAST = "forecast", "Dự báo"

    ward = models.ForeignKey("catalog.Ward", verbose_name="phường/xã", on_delete=models.CASCADE,
                             related_name="weather")
    time = models.DateTimeField("thời điểm", db_index=True)
    kind = models.CharField("loại", max_length=10, choices=Kind.choices)
    temperature = models.FloatField("nhiệt độ (°C)", null=True, blank=True)
    precipitation = models.FloatField("lượng mưa (mm)", null=True, blank=True)
    wind_speed = models.FloatField("gió (km/h)", null=True, blank=True)
    updated_at = models.DateTimeField("cập nhật lúc")

    class Meta:
        verbose_name = "thời tiết theo giờ"
        verbose_name_plural = "thời tiết theo giờ"
        ordering = ["ward", "time", "kind"]
        constraints = [models.UniqueConstraint(fields=["ward", "time", "kind"], name="uniq_weather")]

    def __str__(self):
        return f"{self.ward} {localtime(self.time):%d/%m %H:%M} {self.kind}"
