from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm

from core.models import AuditLog
from core.services import audit

from .models import User


class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "full_name", "phone_number", "role", "rescue_team")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = AdminUserCreationForm
    ordering = ("-date_joined",)
    list_display = ("email", "full_name", "phone_number", "role", "ward", "is_active",
                    "email_verified")
    list_filter = ("role", "is_active", "email_verified")
    search_fields = ("email", "full_name", "phone_number")
    readonly_fields = ("date_joined", "last_login", "is_staff", "is_superuser")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Thông tin", {"fields": ("full_name", "phone_number", "ward", "address_detail",
                                  "home_latitude", "home_longitude", "relative_phone")}),
        ("Vai trò", {"fields": ("role", "rescue_team", "is_active", "email_verified",
                                "is_staff", "is_superuser")}),
        ("Thông báo", {"fields": ("notify_in_app", "notify_email")}),
        ("Thời gian", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",),
                "fields": ("email", "full_name", "phone_number", "role", "rescue_team",
                           "password1", "password2")}),
    )
    filter_horizontal = ()


    def save_model(self, request, obj, form, change):
        old = User.objects.filter(pk=obj.pk).values("role", "is_active").first() if change else None
        if not change:
            obj.email_verified = True
        super().save_model(request, obj, form, change)
        if not change:
            audit(AuditLog.Action.USER_CREATED, actor=request.user, target=obj, request=request,
                  details={"role": obj.role, "via": "django-admin"})
            return
        if old["role"] != obj.role:
            obj.revoke_tokens()
            audit(AuditLog.Action.ROLE_CHANGED, actor=request.user, target=obj, request=request,
                  details={"old_role": old["role"], "new_role": obj.role, "via": "django-admin"})
        if old["is_active"] != obj.is_active:
            if not obj.is_active:
                obj.revoke_tokens()
            audit(AuditLog.Action.USER_LOCKED if not obj.is_active else AuditLog.Action.USER_UNLOCKED,
                  actor=request.user, target=obj, request=request, details={"via": "django-admin"})

    def has_delete_permission(self, request, obj=None):
        return False  # lock accounts instead of deleting them
