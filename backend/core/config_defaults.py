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
    "rapid_rise_threshold_m": (Decimal("0.3"), "m", Decimal("0.01"),
                               "Chỉ để tham khảo: mô hình dùng ngưỡng dâng nhanh lúc huấn luyện "
                               "(models/metadata.json), sửa ở đây không đổi kết quả dự báo"),
    "suspicious_jump_threshold_m": (Decimal("0.8"), "m", Decimal("0.01"),
                                    "Chỉ để tham khảo: du_bao.py dùng ngưỡng nghi ngờ lúc huấn luyện "
                                    "(models/metadata.json), sửa ở đây không đổi kết quả dự báo"),
    "overview_refresh_minutes": (5, "phút", 1, "Chu kỳ tự tải lại trang tổng quan"),
    "stale_data_hours": (2, "giờ", 1, "Số liệu hồ cũ hơn số giờ này thì hiện \"Dữ liệu chưa được cập nhật\" "
                                      "và không hiện dự báo"),
    "warning_reminder_hours": (3, "giờ", 1, "Mức Cảnh báo kéo dài thì nhắc lại sau mỗi số giờ này"),
    "auto_alert_valid_hours": (3, "giờ", 1,
                               "Cảnh báo tự động hết hiệu lực sau số giờ này nếu không được dự báo gia hạn"),
    "forecast_input_hours": (200, "giờ", 170, "Số giờ số liệu gần nhất đưa vào du_bao() (tối thiểu 170)"),
    "history_max_days": (90, "ngày", 1, "Khoảng thời gian tối đa của một lần xem lịch sử hồ chứa"),
    "pctt_min_interval_minutes": (60, "phút", 60, "Khoảng cách tối thiểu giữa hai lần lấy dữ liệu cổng PCTT"),
    "rain_archive_lag_days": (5, "ngày", 1,
                              "Mưa Open-Meteo Historical lấy đến (hôm nay − số ngày này); "
                              "phần gần hơn lấy từ Forecast API"),
    "dispatch_refresh_seconds": (30, "giây", 5, "Chu kỳ tự tải lại màn hình điều phối (giai đoạn 4)"),
}
