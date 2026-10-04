"""Initial values for SystemConfig. They are only used to seed the table (migration
0002) and as a last-resort fallback if a row is missing; admins change the real values
in the database (Django admin or /api/admin/config/)."""
from decimal import Decimal

# key: (default, unit, min_value, description)
DEFAULTS = {
    "sos_self_claim_wait_minutes": (15, "phút", 1,
                                    "Thời gian chờ admin phân công trước khi đội cứu hộ được tự nhận SOS"),
    "sos_anonymize_days": (90, "ngày", 1, "Ẩn danh hoá SOS đã đóng sau số ngày này"),
    "max_failed_logins": (5, "lần", 1, "Số lần đăng nhập sai liên tiếp trước khi tạm khoá"),
    "login_lockout_minutes": (15, "phút", 1, "Thời gian tạm khoá đăng nhập sau khi sai quá số lần"),
    "email_verification_ttl_hours": (24, "giờ", 1, "Hiệu lực đường dẫn xác thực email"),
    "password_reset_ttl_minutes": (30, "phút", 1, "Hiệu lực đường dẫn đặt lại mật khẩu"),
    "jwt_access_minutes": (30, "phút", 1, "Thời hạn mã truy cập (JWT access token)"),
    "jwt_refresh_days": (7, "ngày", 1, "Thời hạn mã làm mới (JWT refresh token)"),
    "rapid_rise_threshold_m": (Decimal("0.3"), "m", Decimal("0.01"), "Ngưỡng dâng nhanh (giai đoạn 2)"),
    "suspicious_jump_threshold_m": (Decimal("0.8"), "m", Decimal("0.01"),
                                    "Mực nước nhảy quá mức này trong 1 giờ thì coi là dữ liệu nghi ngờ (giai đoạn 2)"),
    "overview_refresh_minutes": (5, "phút", 1, "Chu kỳ tự tải lại trang tổng quan (giai đoạn 2)"),
    "dispatch_refresh_seconds": (30, "giây", 5, "Chu kỳ tự tải lại màn hình điều phối (giai đoạn 4)"),
}
