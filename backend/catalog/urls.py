from django.urls import path

from . import views

urlpatterns = [
    path("wards/", views.WardListView.as_view(), name="ward-list"),
    path("admin/rescue-teams/", views.RescueTeamListView.as_view(), name="admin-rescue-team-list"),
]
