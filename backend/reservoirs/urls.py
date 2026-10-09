from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("admin/thresholds", views.AdminThresholdViewSet, basename="admin-threshold")
router.register("admin/directives", views.AdminDirectiveViewSet, basename="admin-directive")

urlpatterns = [
    path("reservoirs/", views.ReservoirListView.as_view(), name="reservoir-list"),
    path("reservoirs/simulation/", views.SimulationInfoView.as_view(), name="reservoir-simulation"),
    path("reservoirs/<str:code>/", views.ReservoirDetailView.as_view(), name="reservoir-detail"),
    path("reservoirs/<str:code>/forecast/", views.ReservoirForecastView.as_view(),
         name="reservoir-forecast"),
    path("reservoirs/<str:code>/history/", views.ReservoirHistoryView.as_view(),
         name="reservoir-history"),
    path("admin/data-status/", views.DataStatusView.as_view(), name="admin-data-status"),
    path("admin/reservoirs/<str:code>/export/", views.ExportView.as_view(),
         name="admin-reservoir-export"),
] + router.urls
