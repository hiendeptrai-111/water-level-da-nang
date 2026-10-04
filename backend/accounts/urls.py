from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("admin/users", views.AdminUserViewSet, basename="admin-user")

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("auth/resend-verification/", views.ResendVerificationView.as_view(),
         name="resend-verification"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/token/refresh/", views.TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/password/forgot/", views.ForgotPasswordView.as_view(), name="password-forgot"),
    path("auth/password/reset/", views.ResetPasswordView.as_view(), name="password-reset"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/change-password/", views.ChangePasswordView.as_view(), name="change-password"),
] + router.urls
