import secrets
import string

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt import serializers as jwt_serializers

from catalog.models import RescueTeam, Ward

from .authentication import is_revoked
from .models import EmailToken, User, normalize_email, phone_validator
from .tokens import RefreshToken

REQUIRED = {"required": "Trường này là bắt buộc.", "blank": "Trường này là bắt buộc.",
            "null": "Trường này là bắt buộc."}
LAT_RANGE, LNG_RANGE = (-90, 90), (-180, 180)


def required_messages(**extra):
    return {**REQUIRED, **extra}


def check_password_strength(password, user=None, field="password"):
    try:
        password_validation.validate_password(password, user)
    except DjangoValidationError as e:
        raise serializers.ValidationError({field: list(e.messages)})


def check_phone_unique(phone, exclude=None):
    qs = User.objects.filter(phone_number=phone)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    if qs.exists():
        raise serializers.ValidationError("Số điện thoại đã được sử dụng.")
    return phone


def check_email_unique(email, exclude=None):
    email = normalize_email(email)
    qs = User.objects.filter(email__iexact=email)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    if qs.exists():
        raise serializers.ValidationError("Email đã được sử dụng.")
    return email


def check_home_location(attrs, instance=None):
    lat = attrs.get("home_latitude", getattr(instance, "home_latitude", None))
    lng = attrs.get("home_longitude", getattr(instance, "home_longitude", None))
    if (lat is None) != (lng is None):
        raise serializers.ValidationError(
            {"home_latitude": "Vị trí nhà phải có cả vĩ độ và kinh độ."})


def random_password(length=12):
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isalpha() for c in pw) and any(c.isdigit() for c in pw):
            return pw


class PhoneField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault("error_messages", required_messages())
        kwargs.setdefault("max_length", 10)
        super().__init__(validators=[phone_validator], **kwargs)

    def to_internal_value(self, data):
        return super().to_internal_value(data).replace(" ", "")


class WardLabelMixin:
    def get_ward_label(self, user):
        return str(user.ward) if user.ward_id else None


# ---------------------------------------------------------------- public account flows
class RegisterSerializer(serializers.Serializer):
    """Self sign-up always creates a citizen. There is no role field: anything else sent
    by the client (role, is_staff, rescue_team...) is ignored."""

    full_name = serializers.CharField(
        min_length=2, max_length=100,
        error_messages=required_messages(min_length="Họ và tên phải từ 2 đến 100 ký tự.",
                                         max_length="Họ và tên phải từ 2 đến 100 ký tự."))
    phone_number = PhoneField()
    email = serializers.EmailField(
        max_length=254, error_messages=required_messages(invalid="Email không đúng định dạng."))
    password = serializers.CharField(write_only=True, trim_whitespace=False,
                                     error_messages=required_messages())
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False,
                                             error_messages=required_messages())
    ward = serializers.PrimaryKeyRelatedField(
        queryset=Ward.objects.all(),
        error_messages=required_messages(does_not_exist="Phường/xã không hợp lệ.",
                                         incorrect_type="Phường/xã không hợp lệ."))
    address_detail = serializers.CharField(
        max_length=255, required=False, allow_blank=True,
        error_messages={"max_length": "Tối đa 255 ký tự."})
    home_latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False,
                                             allow_null=True, min_value=LAT_RANGE[0],
                                             max_value=LAT_RANGE[1])
    home_longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False,
                                              allow_null=True, min_value=LNG_RANGE[0],
                                              max_value=LNG_RANGE[1])
    agree_terms = serializers.BooleanField(error_messages=required_messages())

    def validate_full_name(self, value):
        return " ".join(value.split())

    def validate_phone_number(self, value):
        return check_phone_unique(value)

    def validate_email(self, value):
        return check_email_unique(value)

    def validate_agree_terms(self, value):
        if not value:
            raise serializers.ValidationError("Bạn cần đồng ý với điều khoản để đăng ký.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Mật khẩu nhập lại không khớp."})
        check_password_strength(attrs["password"], User(email=attrs["email"],
                                                        full_name=attrs["full_name"]))
        check_home_location(attrs)
        return attrs

    def create(self, data):
        data.pop("password_confirm")
        data.pop("agree_terms")
        password = data.pop("password")
        return User.objects.create_user(
            password=password, role=User.Role.CITIZEN, email_verified=False,
            terms_accepted_at=timezone.now(), **data)


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(error_messages=required_messages())
    password = serializers.CharField(trim_whitespace=False, error_messages=required_messages())


class IdentifierSerializer(serializers.Serializer):
    identifier = serializers.CharField(error_messages=required_messages())


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages=required_messages(invalid="Email không đúng định dạng."))


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(error_messages=required_messages())


class NewPasswordMixin(serializers.Serializer):
    new_password = serializers.CharField(trim_whitespace=False, error_messages=required_messages())
    new_password_confirm = serializers.CharField(trim_whitespace=False,
                                                 error_messages=required_messages())

    def check_new_password(self, attrs, user):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Mật khẩu nhập lại không khớp."})
        check_password_strength(attrs["new_password"], user, field="new_password")


class ResetPasswordSerializer(NewPasswordMixin, TokenSerializer):
    def validate(self, attrs):
        self.check_new_password(attrs, None)
        return attrs


class ChangePasswordSerializer(NewPasswordMixin):
    old_password = serializers.CharField(trim_whitespace=False, error_messages=required_messages())

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Mật khẩu hiện tại không đúng.")
        return value

    def validate(self, attrs):
        self.check_new_password(attrs, self.context["request"].user)
        return attrs


class TokenRefreshSerializer(jwt_serializers.TokenRefreshSerializer):
    """Uses our config-driven token classes and rejects revoked sessions."""
    token_class = RefreshToken

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        user = User.objects.filter(pk=refresh.payload.get("user_id")).first()
        if user is None or not user.is_active or is_revoked(user, refresh.payload):
            raise AuthenticationFailed("Phiên đăng nhập đã hết hiệu lực, vui lòng đăng nhập lại.",
                                       "session_revoked")
        return super().validate(attrs)


# ---------------------------------------------------------------- profile
class ProfileSerializer(WardLabelMixin, serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    ward_label = serializers.SerializerMethodField()
    rescue_team_name = serializers.CharField(source="rescue_team.name", read_only=True,
                                             default=None)
    pending_email = serializers.SerializerMethodField()
    phone_number = PhoneField()
    relative_phone = PhoneField(required=False, allow_blank=True)
    email = serializers.EmailField(
        max_length=254, error_messages=required_messages(invalid="Email không đúng định dạng."))
    ward = serializers.PrimaryKeyRelatedField(
        queryset=Ward.objects.all(), allow_null=True, required=False,
        error_messages={"does_not_exist": "Phường/xã không hợp lệ.",
                        "incorrect_type": "Phường/xã không hợp lệ."})

    class Meta:
        model = User
        fields = ["id", "full_name", "phone_number", "email", "pending_email", "email_verified",
                  "role", "role_label", "ward", "ward_label", "address_detail",
                  "home_latitude", "home_longitude", "relative_phone",
                  "rescue_team", "rescue_team_name", "notify_in_app", "notify_email",
                  "date_joined"]
        read_only_fields = ["id", "email_verified", "role", "rescue_team", "date_joined"]
        extra_kwargs = {"full_name": {"min_length": 2, "max_length": 100}}

    def get_pending_email(self, user):
        token = (EmailToken.objects
                 .filter(user=user, purpose=EmailToken.Purpose.VERIFY_EMAIL, used_at__isnull=True,
                         expires_at__gt=timezone.now())
                 .exclude(email=user.email).first())
        return token.email if token else None

    def validate_phone_number(self, value):
        return check_phone_unique(value, exclude=self.instance)

    def validate_email(self, value):
        return check_email_unique(value, exclude=self.instance)

    def validate(self, attrs):
        if (self.instance.role == User.Role.CITIZEN and "ward" in attrs
                and attrs["ward"] is None):
            raise serializers.ValidationError({"ward": "Người dân phải chọn phường/xã nơi ở."})
        check_home_location(attrs, self.instance)
        return attrs

    def update(self, instance, data):
        # A new email only replaces the current one after it is verified (see views).
        new_email = data.pop("email", instance.email)
        self.new_email = new_email if new_email != instance.email else None
        return super().update(instance, data)


# ---------------------------------------------------------------- user management (admin)
class AdminUserSerializer(WardLabelMixin, serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    ward_label = serializers.SerializerMethodField()
    rescue_team_name = serializers.CharField(source="rescue_team.name", read_only=True,
                                             default=None)
    phone_number = PhoneField()
    ward = serializers.PrimaryKeyRelatedField(queryset=Ward.objects.all(), allow_null=True,
                                              required=False)

    class Meta:
        model = User
        fields = ["id", "full_name", "phone_number", "email", "email_verified", "role",
                  "role_label", "ward", "ward_label", "rescue_team", "rescue_team_name",
                  "is_active", "date_joined", "last_login"]
        read_only_fields = ["id", "email", "email_verified", "role", "rescue_team", "is_active",
                            "date_joined", "last_login"]

    def validate_phone_number(self, value):
        return check_phone_unique(value, exclude=self.instance)


STAFF_ROLES = [(User.Role.RESCUE_TEAM, "Đội cứu hộ"), (User.Role.ADMIN, "Admin")]


def check_team_for_role(attrs):
    if attrs.get("role") == User.Role.RESCUE_TEAM and not attrs.get("rescue_team"):
        raise serializers.ValidationError(
            {"rescue_team": "Tài khoản đội cứu hộ phải gắn với một đội."})
    if attrs.get("role") != User.Role.RESCUE_TEAM:
        attrs["rescue_team"] = None
    return attrs


class AdminUserCreateSerializer(serializers.Serializer):
    """Admins create rescue-team and admin accounts (they cannot self-register)."""
    full_name = serializers.CharField(min_length=2, max_length=100,
                                      error_messages=required_messages())
    phone_number = PhoneField()
    email = serializers.EmailField(
        max_length=254, error_messages=required_messages(invalid="Email không đúng định dạng."))
    role = serializers.ChoiceField(choices=STAFF_ROLES, error_messages=required_messages(
        invalid_choice="Chỉ tạo được tài khoản đội cứu hộ hoặc admin."))
    rescue_team = serializers.PrimaryKeyRelatedField(
        queryset=RescueTeam.objects.all(), required=False, allow_null=True,
        error_messages={"does_not_exist": "Đội cứu hộ không tồn tại."})
    password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False,
                                     write_only=True)

    def validate_phone_number(self, value):
        return check_phone_unique(value)

    def validate_email(self, value):
        return check_email_unique(value)

    def validate(self, attrs):
        check_team_for_role(attrs)
        if attrs.get("password"):
            check_password_strength(attrs["password"])
        return attrs

    def create(self, data):
        password = data.pop("password", "") or random_password()
        self.generated_password = password
        return User.objects.create_user(password=password, email_verified=True, **data)


class ChangeRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices, error_messages=required_messages())
    rescue_team = serializers.PrimaryKeyRelatedField(
        queryset=RescueTeam.objects.all(), required=False, allow_null=True,
        error_messages={"does_not_exist": "Đội cứu hộ không tồn tại."})

    def validate(self, attrs):
        return check_team_for_role(attrs)


class AdminResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs.get("password"):
            check_password_strength(attrs["password"])
        return attrs
