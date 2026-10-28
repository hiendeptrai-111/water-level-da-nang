"""Initial values for SystemConfig. They are only used to seed the table (migration
0002) and as a last-resort fallback if a row is missing; admins change the real values
in the database (Django admin or /api/admin/config/)."""
from decimal import Decimal

MODEL_BOUND = "Giá trị gắn với mô hình đã huấn luyện, muốn đổi phải huấn luyện lại"
# Shown but never editable (API and Django admin): du_bao/ uses its training constants.
READ_ONLY_KEYS = frozenset({"rapid_rise_threshold_m", "suspicious_jump_threshold_m"})

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
    "rapid_rise_threshold_m": (Decimal("0.3"), "m", Decimal("0.01"), MODEL_BOUND),
    "suspicious_jump_threshold_m": (Decimal("0.8"), "m", Decimal("0.01"), MODEL_BOUND),
    "overview_refresh_minutes": (5, "phút", 1, "Chu kỳ tự tải lại trang tổng quan"),
    "stale_data_hours": (2, "giờ", 1, "Số liệu hồ cũ hơn số giờ này thì hiện \"Dữ liệu chưa được cập nhật\" "
                                      "và không hiện dự báo"),
    "warning_reminder_hours": (3, "giờ", 1, "Mức Cảnh báo kéo dài thì nhắc lại sau mỗi số giờ này"),
    "auto_alert_valid_hours": (3, "giờ", 1,
                               "Cảnh báo tự động hết hiệu lực sau số giờ này nếu không được dự báo gia hạn"),
    "forecast_input_hours": (200, "giờ", 170, "Số giờ số liệu gần nhất đưa vào du_bao() (tối thiểu 170)"),
    "history_max_days": (90, "ngày", 1, "Khoảng thời gian tối đa của một lần xem lịch sử hồ chứa"),
    "pctt_min_interval_minutes": (60, "phút", 60, "Khoảng cách tối thiểu giữa hai lần lấy dữ liệu cổng PCTT"),
    "heavy_rain_threshold_mm": (50, "mm/24 giờ", 1,
                                "Hiển thị biểu tượng \"Mưa lớn\" khi mưa 24 giờ đạt mức này "
                                "(thông tin tham khảo, không phải cảnh báo chính thức)"),
    "rain_archive_lag_days": (5, "ngày", 1,
                              "Mưa Open-Meteo Historical lấy đến (hôm nay − số ngày này); "
                              "phần gần hơn lấy từ Forecast API"),
    "dispatch_refresh_seconds": (30, "giây", 5, "Chu kỳ tự tải lại màn hình điều phối và trang nhiệm vụ"),
    "flood_point_radius_m": (50, "m", 1, "Bán kính ảnh hưởng của một điểm ngập lên các đoạn đường"),
    "flood_slowdown_factor": (Decimal("3"), "lần", Decimal("1"),
                              "Điểm ngập \"xe máy không qua được\": thời gian đi qua đoạn đường nhân hệ số này"),
    "flood_point_ttl_hours": (12, "giờ", 1, "Điểm ngập tự hết hạn sau số giờ này nếu không ai xác nhận lại"),
    "boat_speed_kmh": (20, "km/h", 1, "Tốc độ ca nô (tính theo đường thẳng, giả định đơn giản)"),
    "sos_rate_limit_per_hour": (10, "lần/giờ", 1, "Số lần gửi SOS tối đa mỗi giờ theo thiết bị và theo địa chỉ IP"),
    "sos_photo_max_kb": (2048, "KB", 50, "Dung lượng tối đa của ảnh đính kèm SOS và điểm ngập (sau khi trình duyệt nén)"),
    "team_location_max_age_minutes": (30, "phút", 1,
                                      "Vị trí đội cũ hơn số phút này thì tính đường từ căn cứ của đội"),
    "claim_notify_teams": (3, "đội", 1, "Số đội rảnh gần nhất được báo khi SOS quá thời gian chờ chưa phân công"),
}
