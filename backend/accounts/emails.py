from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail

from core.services import get_config


def _link(path, token):
    return f"{settings.FRONTEND_URL}{path}?{urlencode({'token': token})}"


def send_verification_email(user, token, email=None):
    hours = get_config("email_verification_ttl_hours")
    send_mail(
        "Xác thực email tài khoản cảnh báo lũ Đà Nẵng",
        f"Xin chào {user.full_name},\n\n"
        f"Bấm vào đường dẫn sau để xác thực email của bạn (hiệu lực {hours} giờ):\n"
        f"{_link('/verify-email', token)}\n\n"
        "Nếu bạn không đăng ký tài khoản, hãy bỏ qua email này.",
        None, [email or user.email],
    )


def send_password_reset_email(user, token):
    minutes = get_config("password_reset_ttl_minutes")
    send_mail(
        "Đặt lại mật khẩu tài khoản cảnh báo lũ Đà Nẵng",
        f"Xin chào {user.full_name},\n\n"
        f"Bấm vào đường dẫn sau để đặt mật khẩu mới (dùng một lần, hiệu lực {minutes} phút):\n"
        f"{_link('/reset-password', token)}\n\n"
        "Nếu bạn không yêu cầu, hãy bỏ qua email này; mật khẩu hiện tại vẫn giữ nguyên.",
        None, [user.email],
    )
