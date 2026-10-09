from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("notifications", views.NotificationViewSet, basename="notification")
router.register("admin/alerts", views.AdminAlertViewSet, basename="admin-alert")

urlpatterns = [
    path("alerts/", views.PublicAlertListView.as_view(), name="alert-list"),
] + router.urls
