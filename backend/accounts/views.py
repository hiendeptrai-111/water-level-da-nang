from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from core.models import AuditLog
from core.services import audit, get_config

from . import emails, login_guard
from .models import EmailToken, User
from .permissions import IsAdminRole
from .serializers import (
    AdminResetPasswordSerializer, AdminUserCreateSerializer, AdminUserSerializer,
    ChangePasswordSerializer, ChangeRoleSerializer, EmailSerializer, IdentifierSerializer,
    LoginSerializer, ProfileSerializer, RegisterSerializer, ResetPasswordSerializer,
    TokenSerializer, random_password)
from .tokens import RefreshToken, token_pair

INVALID_CREDENTIALS = "Thông tin đăng nhập không đúng"
INVALID_LINK = "Đường dẫn không hợp lệ, đã được sử dụng hoặc đã hết hạn."
LOGGED_LOGIN_ROLES = (User.Role.ADMIN, User.Role.RESCUE_TEAM)


def error(detail, code, http_status):
    return Response({"detail": detail, "code": code}, status=http_status)


class PublicAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]


def send_verification(user, email=None):
    ttl = timedelta(hours=get_config("email_verification_ttl_hours"))
    raw = EmailToken.issue(user, EmailToken.Purpose.VERIFY_EMAIL, ttl, email=email)
    emails.send_verification_email(user, raw, email=email)


# ---------------------------------------------------------------- sign-up / verification
class RegisterView(PublicAPIView):
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
        send_verification(user)
        return Response({
            "detail": "Đăng ký thành công. Vui lòng mở email để xác thực tài khoản trước khi đăng nhập.",
            "email": user.email,
            "verification_ttl_hours": get_config("email_verification_ttl_hours"),
        }, status=status.HTTP_201_CREATED)


class VerifyEmailView(PublicAPIView):
    throttle_classes = []

    @transaction.atomic
    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = EmailToken.find_valid(serializer.validated_data["token"],
                                      EmailToken.Purpose.VERIFY_EMAIL)
        if token is None:
            return error(INVALID_LINK, "invalid_token", status.HTTP_400_BAD_REQUEST)
        user = token.user
        if token.email != user.email:  # confirming a changed email address
            if User.objects.filter(email__iexact=token.email).exclude(pk=user.pk).exists():
                token.mark_used()
                return error("Email này đã được tài khoản khác sử dụng.", "email_taken",
                             status.HTTP_400_BAD_REQUEST)
            user.email = token.email
        user.email_verified = True
        user.save(update_fields=["email", "email_verified"])
        token.mark_used()
        return Response({"detail": "Xác thực email thành công. Bạn có thể đăng nhập.",
                         "email": user.email})


class ResendVerificationView(PublicAPIView):
    """Always answers the same way, whether the account exists or not."""
    throttle_scope = "resend_verification"

    def post(self, request):
        serializer = IdentifierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.find_by_identifier(serializer.validated_data["identifier"])
        if user is not None and user.is_active and not user.email_verified:
            send_verification(user)
        return Response({"detail": "Nếu tài khoản tồn tại và chưa xác thực, email xác thực mới "
                                   "đã được gửi. Vui lòng kiểm tra hộp thư."})


# ---------------------------------------------------------------- login / tokens
class LoginView(PublicAPIView):
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"].strip()
        password = serializer.validated_data["password"]

        user = User.objects.find_by_identifier(identifier)
        key = login_guard.attempt_key(user, identifier)
        if login_guard.is_locked(key):
            return error(login_guard.locked_message(), "login_locked",
                         status.HTTP_429_TOO_MANY_REQUESTS)

        if user is None:
            make_password(password)  # same hashing cost as a real check
            valid = False
        else:
            valid = user.check_password(password)
        if not valid:
            login_guard.register_failure(key)
            return error(INVALID_CREDENTIALS, "invalid_credentials", status.HTTP_401_UNAUTHORIZED)

        login_guard.reset(key)
        # From here the password is correct, so the specific reasons below reveal nothing
        # to someone who does not already know the password.
        if not user.is_active:
            return error("Tài khoản đã bị khoá. Vui lòng liên hệ quản trị viên.",
                         "account_locked", status.HTTP_403_FORBIDDEN)
        if not user.email_verified:
            return error("Email chưa được xác thực. Vui lòng mở email để xác thực, "
                         "hoặc bấm gửi lại email xác thực.",
                         "email_not_verified", status.HTTP_403_FORBIDDEN)

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        if user.role in LOGGED_LOGIN_ROLES:
            audit(AuditLog.Action.LOGIN, actor=user, target=user, request=request,
                  details={"role": user.role})
        return Response({**token_pair(user), "user": ProfileSerializer(user).data})


class TokenRefreshView(BaseTokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []


class LogoutView(PublicAPIView):
    """Blacklists the refresh token. Works even if the access token has expired."""
    throttle_classes = []

    def post(self, request):
        raw = request.data.get("refresh")
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass  # already invalid or blacklisted: the session is over either way
        return Response({"detail": "Đã đăng xuất."})


# ---------------------------------------------------------------- password
class ForgotPasswordView(PublicAPIView):
    """Same response whether the email exists or not."""
    throttle_scope = "password_forgot"

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"],
                                   is_active=True).first()
        if user is not None:
            ttl = timedelta(minutes=get_config("password_reset_ttl_minutes"))
            raw = EmailToken.issue(user, EmailToken.Purpose.RESET_PASSWORD, ttl)
            emails.send_password_reset_email(user, raw)
        return Response({"detail": "Nếu email có trong hệ thống, đường dẫn đặt lại mật khẩu "
                                   "đã được gửi. Vui lòng kiểm tra hộp thư."})


class ResetPasswordView(PublicAPIView):
    throttle_classes = []

    @transaction.atomic
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = EmailToken.find_valid(serializer.validated_data["token"],
                                      EmailToken.Purpose.RESET_PASSWORD)
        if token is None:
            return error(INVALID_LINK, "invalid_token", status.HTTP_400_BAD_REQUEST)
        user = token.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        user.revoke_tokens()  # every old session is logged out
        token.mark_used()
        login_guard.reset(login_guard.attempt_key(user, ""))
        return Response({"detail": "Đặt mật khẩu mới thành công. Vui lòng đăng nhập lại."})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        user.revoke_tokens()
        # New tokens so this device stays logged in; every other session is invalidated.
        return Response({"detail": "Đổi mật khẩu thành công.", **token_pair(user)})


# ---------------------------------------------------------------- profile
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        user = serializer.save()
        if serializer.new_email:
            send_verification(user, email=serializer.new_email)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        user = self.get_object()
        response.data = ProfileSerializer(user).data
        if response.data.get("pending_email"):
            response.data["detail"] = (f"Đã gửi email xác thực đến {response.data['pending_email']}. "
                                       "Email mới chỉ được dùng sau khi xác thực.")
        return response


# ---------------------------------------------------------------- user management (CN23)
class AdminUserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                       mixins.CreateModelMixin, mixins.UpdateModelMixin,
                       viewsets.GenericViewSet):
    """Admin only. No delete: accounts are locked instead, to keep the history."""
    permission_classes = [IsAdminRole]
    serializer_class = AdminUserSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = User.objects.select_related("ward", "rescue_team")
        params = self.request.query_params
        if params.get("role"):
            qs = qs.filter(role=params["role"])
        if params.get("is_active") in ("true", "false"):
            qs = qs.filter(is_active=params["is_active"] == "true")
        q = params.get("search", "").strip()
        if q:
            qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q)
                           | Q(phone_number__icontains=q))
        return qs

    def create(self, request, *args, **kwargs):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
            audit(AuditLog.Action.USER_CREATED, actor=request.user, target=user, request=request,
                  details={"role": user.role, "rescue_team": user.rescue_team_id})
        data = AdminUserSerializer(user).data
        data["temporary_password"] = serializer.generated_password  # shown once
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        before = {f: getattr(serializer.instance, f) for f in ("full_name", "phone_number", "ward_id")}
        user = serializer.save()
        changed = {f: [str(v), str(getattr(user, f))] for f, v in before.items()
                   if v != getattr(user, f)}
        if changed:
            audit(AuditLog.Action.USER_UPDATED, actor=self.request.user, target=user,
                  request=self.request, details=changed)

    def _guard_self(self, user, what):
        if user.pk == self.request.user.pk:
            return error(f"Không thể {what} chính tài khoản của bạn.", "self_action",
                         status.HTTP_400_BAD_REQUEST)
        return None

    def _is_last_admin(self, user):
        return (user.role == User.Role.ADMIN and
                not User.objects.filter(role=User.Role.ADMIN, is_active=True)
                .exclude(pk=user.pk).exists())

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def lock(self, request, pk=None):
        user = self.get_object()
        if (resp := self._guard_self(user, "khoá")):
            return resp
        if self._is_last_admin(user):
            return error("Không thể khoá admin cuối cùng.", "last_admin", status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.save(update_fields=["is_active"])
        user.revoke_tokens()
        audit(AuditLog.Action.USER_LOCKED, actor=request.user, target=user, request=request,
              details={"reason": request.data.get("reason", "")[:255]})
        return Response(AdminUserSerializer(user).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def unlock(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        login_guard.reset(login_guard.attempt_key(user, ""))
        audit(AuditLog.Action.USER_UNLOCKED, actor=request.user, target=user, request=request)
        return Response(AdminUserSerializer(user).data)

    @action(detail=True, methods=["post"], url_path="change-role")
    @transaction.atomic
    def change_role(self, request, pk=None):
        user = self.get_object()
        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role, team = serializer.validated_data["role"], serializer.validated_data["rescue_team"]
        if new_role != user.role:
            if (resp := self._guard_self(user, "đổi vai trò")):
                return resp
            if self._is_last_admin(user):
                return error("Không thể đổi vai trò của admin cuối cùng.", "last_admin",
                             status.HTTP_400_BAD_REQUEST)
        old_role, old_team = user.role, user.rescue_team_id
        user.role, user.rescue_team = new_role, team
        user.save()
        if old_role != new_role:
            user.revoke_tokens()  # the role is in the token: force a fresh login
        audit(AuditLog.Action.ROLE_CHANGED, actor=request.user, target=user, request=request,
              details={"old_role": old_role, "new_role": new_role,
                       "old_rescue_team": old_team, "new_rescue_team": user.rescue_team_id})
        return Response(AdminUserSerializer(user).data)

    @action(detail=True, methods=["post"], url_path="reset-password")
    @transaction.atomic
    def reset_password(self, request, pk=None):
        user = self.get_object()
        serializer = AdminResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.get("password") or random_password()
        user.set_password(password)
        user.save(update_fields=["password"])
        user.revoke_tokens()
        login_guard.reset(login_guard.attempt_key(user, ""))
        audit(AuditLog.Action.PASSWORD_RESET_BY_ADMIN, actor=request.user, target=user,
              request=request)
        return Response({"detail": "Đã đặt lại mật khẩu. Mật khẩu chỉ hiển thị một lần.",
                         "temporary_password": password})
