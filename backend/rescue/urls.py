from django.urls import path

from . import views

urlpatterns = [
    # sender (CN15, CN16)
    path("sos/", views.SOSCreateView.as_view(), name="sos-create"),
    path("sos/mine/", views.MySOSView.as_view(), name="sos-mine"),
    path("sos/<str:code>/", views.SOSDetailView.as_view(), name="sos-detail"),
    path("sos/<str:code>/cancel/", views.SOSCancelView.as_view(), name="sos-cancel"),
    path("sos/<str:code>/photo/", views.SOSPhotoUploadView.as_view(), name="sos-photo-upload"),
    # dispatch, admin (CN17, CN18)
    path("dispatch/sos/", views.DispatchListView.as_view(), name="dispatch-list"),
    path("dispatch/sos/<int:pk>/", views.DispatchDetailView.as_view(), name="dispatch-detail"),
    path("dispatch/sos/<int:pk>/suggestions/", views.DispatchSuggestView.as_view(), name="dispatch-suggest"),
    path("dispatch/sos/<int:pk>/photo/", views.SOSPhotoView.as_view(), name="sos-photo"),
    path("dispatch/sos/<int:pk>/<str:action>/", views.DispatchActionView.as_view(), name="dispatch-action"),
    # rescue team (CN19)
    path("rescue/tasks/", views.TeamTasksView.as_view(), name="team-tasks"),
    path("rescue/tasks/<int:pk>/<str:action>/", views.TeamTaskActionView.as_view(), name="team-task-action"),
    path("rescue/location/", views.TeamLocationView.as_view(), name="team-location"),
    path("rescue/status/", views.TeamStatusView.as_view(), name="team-status"),
    # flood points (CN20, CN21)
    path("flood-points/", views.FloodPointsView.as_view(), name="flood-points"),
    path("flood-points/<int:pk>/confirm/", views.FloodConfirmView.as_view(), name="flood-confirm"),
    path("admin/flood-points/", views.AdminFloodListView.as_view(), name="admin-flood-list"),
    path("admin/flood-points/<int:pk>/photo/", views.FloodPhotoView.as_view(), name="admin-flood-photo"),
    path("admin/flood-points/<int:pk>/<str:action>/", views.AdminFloodActionView.as_view(), name="admin-flood-action"),
]
