from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Quản trị hệ thống cảnh báo lũ Đà Nẵng"
admin.site.site_title = "Quản trị"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("catalog.urls")),
    path("api/", include("core.urls")),
]
