from django.urls import path

from . import views

urlpatterns = [
    path("weather/wards/<int:pk>/", views.WardWeatherView.as_view(), name="weather-ward"),
    path("weather/map/", views.WeatherMapView.as_view(), name="weather-map"),
    path("weather/boundaries/", views.ward_boundaries, name="weather-boundaries"),
]
