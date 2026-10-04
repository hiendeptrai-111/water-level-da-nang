import hashlib
import secrets

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

phone_validator = RegexValidator(
    r"^0\d{9}$", "Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0."
)


def normalize_email(email):
    """Emails are compared case-insensitively: store the whole address lower-cased."""
    return (email or "").strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_email(self, email):
        return self.get(email__iexact=normalize_email(email))

    def find_by_identifier(self, identifier):
        """Email or phone number -> user, or None."""
        identifier = (identifier or "").strip()
        if not identifier:
            return None
        if "@" in identifier:
            return self.filter(email__iexact=normalize_email(identifier)).first()
        return self.filter(phone_number=identifier).first()

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email là bắt buộc")
        user = self.model(email=normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.update(role=User.Role.ADMIN, email_verified=True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CITIZEN = "citizen", "Người dân"
        RESCUE_TEAM = "rescue_team", "Đội cứu hộ"
        ADMIN = "admin", "Admin"

    full_name = models.CharField("họ và tên", max_length=100)
    phone_number = models.CharField("số điện thoại", max_length=10, unique=True,
                                    validators=[phone_validator])
    email = models.EmailField("email", max_length=254, unique=True)
    email_verified = models.BooleanField("đã xác thực email", default=False)
    role = models.CharField("vai trò", max_length=20, choices=Role.choices, default=Role.CITIZEN,
                            db_index=True)
    ward = models.ForeignKey("catalog.Ward", verbose_name="phường/xã nơi ở", on_delete=models.PROTECT,
                             null=True, blank=True, related_name="residents")
    address_detail = models.CharField("số nhà, thôn/tổ", max_length=255, blank=True)
    home_latitude = models.DecimalField("vĩ độ nhà", max_digits=9, decimal_places=6,
                                        null=True, blank=True)
    home_longitude = models.DecimalField("kinh độ nhà", max_digits=9, decimal_places=6,
                                         null=True, blank=True)
    relative_phone = models.CharField("số điện thoại người thân", max_length=10, blank=True,
                                      validators=[phone_validator])
    rescue_team = models.ForeignKey("catalog.RescueTeam", verbose_name="đội cứu hộ",
                                    on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="members")
    notify_in_app = models.BooleanField("nhận thông báo trên website", default=True)
    notify_email = models.BooleanField("nhận thông báo qua email", default=True)
    terms_accepted_at = models.DateTimeField("đồng ý điều khoản lúc", null=True, blank=True)

    is_active = models.BooleanField("đang hoạt động", default=True,
                                    help_text="Bỏ chọn để khoá tài khoản.")
    is_staff = models.BooleanField("vào được trang Django admin", default=False)
    date_joined = models.DateTimeField("ngày tạo", default=timezone.now)
    # Tokens carry this number in the "ver" claim; bumping it (password change, lock...)
    # invalidates every token issued before.
    token_version = models.PositiveIntegerField(default=0, editable=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "phone_number"]

    class Meta:
        verbose_name = "người dùng"
        verbose_name_plural = "người dùng"
        ordering = ["-date_joined"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="uniq_user_email_ci"),
            models.CheckConstraint(
                condition=Q(rescue_team__isnull=True) | Q(role="rescue_team"),
                name="rescue_team_only_for_rescue_role",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        if self.role != self.Role.RESCUE_TEAM:
            self.rescue_team = None
        # Django admin site access follows the application role.
        self.is_staff = self.is_superuser = self.role == self.Role.ADMIN
        super().save(*args, **kwargs)

    def revoke_tokens(self):
        """Invalidate every token issued so far (refresh tokens are blacklisted too)."""
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken, OutstandingToken)
        now = timezone.now()
        User.objects.filter(pk=self.pk).update(token_version=models.F("token_version") + 1)
        self.refresh_from_db(fields=["token_version"])
        for token in OutstandingToken.objects.filter(user=self, expires_at__gt=now):
            BlacklistedToken.objects.get_or_create(token=token)


def hash_token(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


class EmailToken(models.Model):
    """Single-use link token (email verification / password reset). Only the hash is stored."""

    class Purpose(models.TextChoices):
        VERIFY_EMAIL = "verify_email", "Xác thực email"
        RESET_PASSWORD = "reset_password", "Đặt lại mật khẩu"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_tokens")
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    # Address the link was sent to (differs from user.email while an email change is pending).
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def issue(cls, user, purpose, ttl, email=None):
        """Create a new token, invalidating the user's earlier unused ones of the same purpose."""
        now = timezone.now()
        cls.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=now)
        raw = secrets.token_urlsafe(32)
        cls.objects.create(user=user, purpose=purpose, token_hash=hash_token(raw),
                           email=normalize_email(email or user.email), expires_at=now + ttl)
        return raw

    @classmethod
    def find_valid(cls, raw, purpose):
        """Unused, unexpired token or None."""
        if not raw:
            return None
        return (cls.objects.select_related("user")
                .filter(token_hash=hash_token(raw), purpose=purpose, used_at__isnull=True,
                        expires_at__gt=timezone.now())
                .first())

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])


class LoginAttempt(models.Model):
    """Consecutive failed logins per key. The key is the user id when the identifier matches
    an account, otherwise the identifier itself, so non-existent accounts are locked the same
    way and responses never reveal whether an account exists."""

    key = models.CharField(max_length=255, unique=True)
    failures = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
