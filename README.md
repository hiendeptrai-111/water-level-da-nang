# Hệ thống cảnh báo lũ và cứu hộ khẩn cấp Đà Nẵng

Website theo tài liệu đặc tả `docs/dac_ta_chuc_nang.md`, làm theo 5 giai đoạn (mục 8 của đặc tả).

**Trạng thái: đã xong Giai đoạn 1 và Giai đoạn 2.**

- Giai đoạn 1: CN01–CN05 (tài khoản), CN23 (quản lý người dùng), CN28 (nhật ký hệ thống).
- Giai đoạn 2: CN06–CN10 (hồ chứa, dự báo, cảnh báo tự động), CN12 (lịch sử cảnh báo), CN24 (ngưỡng và chỉ đạo), CN27 (tình trạng dữ liệu và mô hình).

```
water-level-da-nang/
├── backend/     Django + DRF + JWT, PostgreSQL
│   ├── config/      settings (đọc .env), urls
│   ├── accounts/    User, đăng ký/đăng nhập/xác thực email/mật khẩu, hồ sơ, quản lý người dùng
│   ├── catalog/     Ward (phường/xã), RescueTeam (đội cứu hộ, bản tối thiểu)
│   ├── core/        SystemConfig (tham số), AuditLog (nhật ký chỉ thêm)
│   ├── reservoirs/  Hồ chứa, số liệu vận hành, mưa, dự báo, ngưỡng, chỉ đạo, quy trình mỗi giờ
│   ├── alerts/      Cảnh báo, thông báo, cảnh báo tự động (CN10)
│   └── data/wards.csv   94 đơn vị theo Nghị quyết 1659/NQ-UBTVQH15 (có ghi nguồn)
├── frontend/    React (Vite) + React Router + Leaflet + Recharts
├── du_bao/      Module dự báo chép từ thư mục nghiên cứu (xem du_bao/NGUON.md), KHÔNG sửa
├── kho_du_lieu/ Kho dữ liệu (không commit, nằm trong .gitignore), xem mục 4
└── docs/        Tài liệu đặc tả
```

## Yêu cầu

- Python 3.12, Node.js 20 trở lên
- PostgreSQL (Postgres.app, PostgreSQL 18), database `water_level`, user `water`

## 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt     # gồm cả numpy/pandas/scikit-learn/xgboost đúng phiên bản lúc huấn luyện

cp .env.example .env
# Mở .env để điền:
#   DJANGO_SECRET_KEY: tạo bằng lệnh
#       python -c "import secrets; print(secrets.token_urlsafe(50))"
#   DB_PASSWORD: mật khẩu của user water (Postgres.app cấu hình mặc định "trust"
#                trên localhost nên để trống vẫn kết nối được)

python manage.py migrate            # tạo bảng, nạp giá trị ban đầu của SystemConfig
python manage.py load_wards         # nạp 94 phường/xã/đặc khu (chạy lại nhiều lần không bị trùng)
python manage.py seed_demo_data     # DỮ LIỆU DEMO: in ra các tài khoản và mật khẩu mẫu (từ chối chạy khi DEBUG=false)
python manage.py runserver          # http://localhost:8000
```

Cần thêm một admin thật (không phải demo) thì chạy `python manage.py createsuperuser`, rồi nhập email, họ tên, số điện thoại và mật khẩu.

**Email:** khi phát triển, email (xác thực, đặt lại mật khẩu, cảnh báo tự động) được **in ra terminal** đang chạy lệnh; mở đường dẫn trong đó để xác thực. Dùng SMTP thật thì sửa `EMAIL_BACKEND` và các biến `EMAIL_*` trong `.env`.

**Trang quản trị Django:** http://localhost:8000/django-admin/ (đăng nhập bằng tài khoản admin). Tại đây xem nhật ký hệ thống, số liệu, kết quả dự báo (chỉ xem), sửa tham số cấu hình và nhập tọa độ đập.

## 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env     # không bắt buộc, giá trị mặc định đã dùng được
npm run dev              # http://localhost:5173
```

Vite chuyển tiếp các request `/api` sang `http://localhost:8000`, nên phải chạy backend trước.

## 3. Tài khoản demo

`python manage.py seed_demo_data` tạo (mật khẩu chung: `Demo12345`, **chỉ để thử**). Lệnh từ chối chạy khi `DJANGO_DEBUG=false`.

| Vai trò | Email | Số điện thoại | Ghi chú |
|---|---|---|---|
| Admin | admin@demo.example.com | 0900000001 | |
| Đội cứu hộ | doi1@demo.example.com | 0900000011 | Đội Đại Lộc: xe cứu hộ, xe máy |
| Đội cứu hộ | doi2@demo.example.com | 0900000012 | Đội Hội An: ca nô, xe máy |
| Người dân | dan1@demo.example.com | 0900000021 | Xã Đại Lộc |
| Người dân | dan2@demo.example.com | 0900000022 | Xã Duy Xuyên |
| Người dân | dan3@demo.example.com | 0900000023 | Phường Hội An |

Đăng nhập bằng email **hoặc** số điện thoại. Sau khi đăng nhập: người dân về `/`, đội cứu hộ về `/rescue/tasks`, admin về `/admin`.

## 4. Dữ liệu và dự báo (giai đoạn 2)

### Kho dữ liệu `kho_du_lieu/`

Kho dữ liệu được **sao chép** từ thư mục nghiên cứu `~/Documents/data/`; bản gốc giữ nguyên. Kho không được commit vì nằm trong `.gitignore`.

| Đường dẫn | Nội dung |
|---|---|
| `kho_du_lieu/van_hanh/van_hanh.csv` | Số liệu vận hành 4 hồ theo giờ, 02/08/2017 → nay (đã bỏ trùng mốc giờ bằng `xl.bo_trung_moc_gio`). Lệnh cập nhật mỗi giờ thêm giờ mới vào đây. |
| `kho_du_lieu/van_hanh/tho/` | JSON gốc nhận từ cổng PCTT, mỗi lần lấy một file, không ghi đè |
| `kho_du_lieu/mua_data/` | Mưa dùng để huấn luyện, 01/01/2016 → 31/12/2025 |
| `kho_du_lieu/ngoai_le_thu_cong.csv` | Các đoạn số liệu loại trừ thủ công |
| `kho_du_lieu/mua_tai_them/` | JSON gốc của mọi lần tải mưa Open-Meteo (Historical và Forecast) |

Đường dẫn trong `du_bao/` tính theo vị trí file của module, nên mặc định module tìm dữ liệu trong `du_bao/kho_du_lieu`. Backend không sửa file nào trong `du_bao/`: `reservoirs/forecasting.py` import module rồi trỏ các đường dẫn đó sang `kho_du_lieu/`. Mọi bước làm sạch dữ liệu đều gọi lại hàm gốc trong `du_bao/`:

- Bỏ trùng mốc giờ: `xl.bo_trung_moc_gio`, chạy bên trong `cap_nhat_du_lieu_ho.cap_nhat()`.
- Phạm vi, loại trừ thủ công, lọc gai, nội suy: `xl.nap_du_lieu_sach`, dùng để đánh dấu số liệu nghi ngờ.
- Lọc gai thời gian thực: chạy bên trong `du_bao()`.

### Mưa

Mưa của một hồ là trung bình cộng các điểm trong `du_bao/models/toa_do_mua.json`. Cấu hình tải giống hệt lúc huấn luyện: `hourly=precipitation`, `timezone=Asia/Bangkok`, không chỉ định model. Mình đã kiểm tra: tải lại tuần 25–31/10/2025 bằng Archive API thì khớp dữ liệu huấn luyện 168/168 giờ.

Có hai nguồn, và mỗi giờ ghi rõ nguồn của nó (`Rainfall.source`):

- Đến (hôm nay − 5 ngày): lấy từ Historical API (`historical`).
- Phần gần đây hơn: lấy từ Forecast API, tham số `past_days` (`forecast`).

Khi cùng một giờ có cả hai nguồn, số liệu Historical luôn được ưu tiên.

### Lệnh, theo thứ tự

```bash
cd backend && source .venv/bin/activate
python manage.py load_reservoirs      # 4 hồ, ngưỡng A.1/A.2, chỉ đạo ví dụ A.4 (đã hết hiệu lực), liên kết Phụ lục B
python manage.py load_history         # kho_du_lieu -> cơ sở dữ liệu, đánh dấu số liệu nghi ngờ (~40 giây)
python manage.py fetch_rain_history   # bù mưa sau 31/12/2025, rồi báo số giờ còn thiếu
python manage.py update_forecasts     # chạy 1 lần quy trình mỗi giờ, in dòng cron mẫu
python manage.py replay_forecasts --from 2025-10-01 --to 2025-10-31   # dữ liệu mô phỏng để trình diễn (~2 phút)
```

Ba lệnh nạp (`load_*`, `fetch_rain_history`) chạy lại nhiều lần không bị nhân đôi.

**Quy trình mỗi giờ (`update_forecasts`)** chạy lần lượt các bước sau:

1. Lấy dữ liệu từ cổng PCTT bằng `cap_nhat_du_lieu_ho.cap_nhat()`. Mỗi giờ gọi tối đa 1 lần, User-Agent ghi tên dự án.
2. Lấy mưa Historical cho những ngày còn thiếu.
3. Lấy mưa Forecast (`past_days=7`), chỉ lưu đến giờ hiện tại.
4. Đánh dấu số liệu nghi ngờ.
5. Gọi `du_bao()` cho 4 hồ trên 200 giờ gần nhất (tối thiểu 170) đọc từ cơ sở dữ liệu.
6. Lưu kết quả vào `Forecast`.
7. Tạo cảnh báo và thông báo.

Mỗi bước, và mỗi hồ trong từng bước, được ghi vào `UpdateRun`. Một hồ lỗi không làm dừng các hồ khác. Mức cảnh báo lấy nguyên từ kết quả `du_bao()`, chỉ đổi tên mức: `binh_thuong` → `normal`, `theo_doi` → `watch`, `canh_bao` → `warning`.

Lệnh **không tự bật cron**. Muốn chạy tự động thì tạo thư mục `backend/logs/`, rồi thêm dòng mà `python manage.py update_forecasts --print-cron` in ra bằng `crontab -e`. Ví dụ:

```
20 * * * * cd /đường/dẫn/backend && .venv/bin/python manage.py update_forecasts >> logs/update_forecasts.log 2>&1
```

**Phát lại (`replay_forecasts`)** dùng để trình diễn khi thời tiết hiện tại bình thường:

- Lệnh dự báo lại từng giờ trên dữ liệu lịch sử. Ở giờ t, `du_bao()` chỉ nhận dữ liệu đến giờ t.
- Kết quả lưu với `is_simulation=True` nên không ghi đè kết quả thật, và không bao giờ gửi email.
- Mỗi lần chạy, các cảnh báo mô phỏng của lần phát lại trước bị xoá.
- Muốn thử chuông thông báo thì thêm `--web-notifications`.
- Giao diện có nút "Xem dữ liệu mô phỏng". Khi đang xem, một dải màu tím ghi rõ "DỮ LIỆU MÔ PHỎNG".

### Cảnh báo tự động (CN10)

- Hệ thống chỉ tạo thông báo khi mức tăng lên (bình thường → theo dõi → cảnh báo).
- Nếu mức "Cảnh báo" kéo dài, hệ thống nhắc lại sau mỗi 3 giờ dự báo (`warning_reminder_hours`).
- Admin nhận cả mức "Theo dõi" và "Cảnh báo". Đội cứu hộ chỉ nhận mức "Cảnh báo". Người dân xem các cảnh báo mức "Cảnh báo" trên trang `/alerts`.
- Thông báo gửi qua website (chuông trên thanh điều hướng, có nút "Đã xem" và lưu thời điểm xem) và qua email.
- Mức "Khẩn cấp" do admin phát là phần của giai đoạn 5, chưa làm.

### Tham số mới trong SystemConfig

Các khoá mới đặt tên theo cùng quy ước với các khoá đã có. Admin sửa được các tham số này.

| Khoá | Mặc định | Ý nghĩa |
|---|---|---|
| `stale_data_hours` | 2 giờ | Số liệu cũ hơn mức này thì hiện "Dữ liệu chưa được cập nhật" và không hiện dự báo |
| `warning_reminder_hours` | 3 giờ | Chu kỳ nhắc lại khi mức Cảnh báo kéo dài |
| `auto_alert_valid_hours` | 3 giờ | Cảnh báo tự động hết hiệu lực nếu không được gia hạn |
| `forecast_input_hours` | 200 giờ | Số giờ đưa vào `du_bao()` (tối thiểu 170) |
| `history_max_days` | 90 ngày | Khoảng thời gian tối đa của một lần xem lịch sử |
| `pctt_min_interval_minutes` | 60 phút | Khoảng cách tối thiểu giữa hai lần gọi cổng PCTT |
| `rain_archive_lag_days` | 5 ngày | Mưa Historical lấy đến (hôm nay − số ngày này) |

Hai khoá `rapid_rise_threshold_m` (0,3 m) và `suspicious_jump_threshold_m` (0,8 m) **chỉ để tham khảo**: mô hình dùng các giá trị cố định lúc huấn luyện (`models/metadata.json`), nên sửa hai khoá này không thay đổi kết quả dự báo.

## 5. Chạy test

User `water` cần quyền tạo database tạm `test_water_level`. Cấp quyền một lần:

```bash
psql -h localhost -d postgres -c "ALTER ROLE water CREATEDB;"
```

Rồi chạy:

```bash
cd backend && source .venv/bin/activate
python manage.py test
```

Nếu không muốn cấp quyền, chạy test bằng một user đã có sẵn quyền đó. Ví dụ với Postgres.app: `DB_USER=$(whoami) python manage.py test`.

Test của giai đoạn 2 không cần `kho_du_lieu/`: test tạo một kho dữ liệu tổng hợp trong thư mục tạm rồi nạp bằng chính các lệnh trên. Nếu máy có `kho_du_lieu/`, test (b) chạy thêm một lần trên dữ liệu thật tháng 10/2025.

## 6. API

### Giai đoạn 1

| Phương thức, đường dẫn | Quyền | Chức năng |
|---|---|---|
| `POST /api/auth/register/` | Công khai, giới hạn tần suất | Đăng ký người dân (không có trường vai trò) |
| `POST /api/auth/verify-email/` | Công khai | Xác thực email `{token}` |
| `POST /api/auth/resend-verification/` | Công khai, giới hạn tần suất | Gửi lại email xác thực `{identifier}` |
| `POST /api/auth/login/` | Công khai, giới hạn tần suất | `{identifier, password}`, identifier là email hoặc số điện thoại |
| `POST /api/auth/token/refresh/` | Công khai | Làm mới access token |
| `POST /api/auth/logout/` | Công khai | Đưa refresh token vào danh sách đen |
| `POST /api/auth/password/forgot/` | Công khai, giới hạn tần suất | Gửi email đặt lại mật khẩu |
| `POST /api/auth/password/reset/` | Công khai | `{token, new_password, new_password_confirm}` |
| `GET/PATCH /api/me/` | Đã đăng nhập | Xem/sửa hồ sơ (đổi email phải xác thực email mới) |
| `POST /api/me/change-password/` | Đã đăng nhập | Đổi mật khẩu (các phiên khác bị đăng xuất) |
| `GET /api/wards/?search=` | Công khai | 94 phường/xã, vùng hạ du lên đầu, tìm không dấu |
| `GET/POST/PATCH /api/admin/users/` | Admin | Danh sách, tạo tài khoản đội cứu hộ/admin, sửa |
| `POST /api/admin/users/{id}/lock/`, `unlock/`, `change-role/`, `reset-password/` | Admin | Khoá, mở khoá, đổi vai trò, đặt lại mật khẩu |
| `GET /api/admin/rescue-teams/` | Admin | Danh sách đội cứu hộ |
| `GET /api/admin/config/`, `PATCH /api/admin/config/{key}/` | Admin | Tham số hệ thống |
| `GET /api/admin/audit-logs/` | Admin | Nhật ký (chỉ đọc) |

### Giai đoạn 2

Các API công khai không cần đăng nhập và không trả thông tin cá nhân. Mọi API có `?simulation=1&at=YYYY-MM-DDTHH:MM` thì trả dữ liệu mô phỏng như ở thời điểm `at`.

| Phương thức, đường dẫn | Quyền | Chức năng |
|---|---|---|
| `GET /api/reservoirs/` | Công khai | 4 hồ (CN06), kèm chu kỳ tự tải lại |
| `GET /api/reservoirs/{code}/` | Công khai | Tình trạng hồ, bảng dự báo, thông tin mô hình (CN07) |
| `GET /api/reservoirs/{code}/forecast/` | Công khai | Bảng dự báo 1/3/6 giờ, so sánh với ngưỡng và mục tiêu điều hành |
| `GET /api/reservoirs/{code}/history/?from=&to=` | Công khai | Số liệu và mưa theo giờ (mặc định 7 ngày, tối đa 90 ngày) |
| `GET /api/reservoirs/simulation/` | Công khai | Khoảng thời gian có dữ liệu mô phỏng |
| `GET /api/alerts/` | Công khai | Cảnh báo đang hiệu lực (CN09); người dân đã đăng nhập thấy phường/xã mình lên đầu |
| `GET /api/notifications/?unseen=1` | Đã đăng nhập | Thông báo trên website của mình, kèm `unseen_count` |
| `POST /api/notifications/{id}/seen/`, `POST /api/notifications/seen-all/` | Đã đăng nhập | Đánh dấu đã xem |
| `GET /api/admin/alerts/?reservoir=&level=&source=&from=&to=&simulation=&active=` | Admin | Lịch sử cảnh báo (CN12); xem chi tiết tại `/{id}/`, gồm dự báo và người nhận |
| `GET /api/admin/thresholds/`, `PATCH /api/admin/thresholds/{id}/` | Admin | Ngưỡng quy định (CN24), ghi nhật ký |
| `GET/POST /api/admin/directives/`, `POST /api/admin/directives/{id}/deactivate/` | Admin | Chỉ đạo điều hành: thêm, đánh dấu hết hiệu lực. **Không** có sửa/xoá (405) |
| `GET /api/admin/data-status/` | Admin | Tình trạng dữ liệu và mô hình (CN27) |
| `GET /api/admin/reservoirs/{code}/export/?from=&to=&simulation=` | Admin | Xuất CSV (UTF-8 BOM, mở được bằng Excel) (CN08) |

Mỗi kết quả hồ chứa đều kèm các trường sau:

- `data_time`: thời điểm của số liệu.
- `stale`: `true` khi số liệu cũ hơn 2 giờ.
- `thresholds`: ngưỡng quy định của thời kỳ hiện tại, hoặc `in_season=false` / "Ngoài mùa lũ".
- `directives`: các chỉ đạo đang hiệu lực.

Khi giờ mới nhất không có mực nước, hoặc số liệu đã cũ, API không trả dự báo: `forecast_available=false` và `forecast_message = "Chưa đủ dữ liệu để dự báo"`.

## 7. Bảng đối chiếu tên

Code dùng tên tiếng Anh; giao diện hoàn toàn bằng tiếng Việt. Cột 1 là tên hoặc mã trong `docs/dac_ta_chuc_nang.md` (hoặc tên mô tả trong yêu cầu), cột 2 là tên trong code.

### Chức năng, màn hình, API

| Đặc tả | Code |
|---|---|
| CN01 Đăng ký, `/dang-ky` | `POST /api/auth/register/`, màn hình `/register` |
| CN02 Đăng nhập, `/dang-nhap` | `POST /api/auth/login/`, màn hình `/login` |
| CN03 Quên mật khẩu, `/quen-mat-khau` | `/api/auth/password/forgot/`, `/api/auth/password/reset/`; màn hình `/forgot-password`, `/reset-password` |
| CN04 Hồ sơ cá nhân, `/tai-khoan` | `GET/PATCH /api/me/`, màn hình `/account` |
| CN05 Đăng xuất | `POST /api/auth/logout/` |
| CN06 Tổng quan hồ chứa, `/` | `GET /api/reservoirs/`, màn hình `/` (`HomePage`) |
| CN07 Chi tiết và dự báo, `/ho-chua/:ma` | `/api/reservoirs/{code}/`, `.../forecast/`, `.../history/`; màn hình `/reservoirs/:code` |
| CN08 Tải dữ liệu hồ chứa | `GET /api/admin/reservoirs/{code}/export/`, nút "Tải CSV" trên `/reservoirs/:code` (admin) |
| CN09 Cảnh báo khu vực, `/canh-bao` | `GET /api/alerts/`, màn hình `/alerts` |
| CN10 Cảnh báo tự động | `alerts.services.evaluate`; `/api/notifications/`; chuông thông báo (`NotificationBell`) |
| CN12 Lịch sử cảnh báo, `/admin/canh-bao` | `/api/admin/alerts/`, màn hình `/admin/alerts` |
| CN19 Nhiệm vụ cứu hộ, `/cuu-ho/nhiem-vu` | màn hình `/rescue/tasks` (giữ chỗ, giai đoạn 4) |
| CN23 Quản lý người dùng, `/admin/nguoi-dung` | `/api/admin/users/`, màn hình `/admin/users` |
| CN24 Hồ chứa và ngưỡng, `/admin/nguong` (đặc tả: `/admin/danh-muc`) | `/api/admin/thresholds/`, `/api/admin/directives/`, màn hình `/admin/thresholds` |
| CN27 Tình trạng dữ liệu và mô hình, `/admin` | `GET /api/admin/data-status/`, màn hình `/admin` |
| CN28 Nhật ký hệ thống | `core.AuditLog`, `/api/admin/audit-logs/`, Django admin |
| `/api/ho-chua/`, `/api/ho-chua/<ma>/` | `/api/reservoirs/`, `/api/reservoirs/{code}/` |
| `/api/ho-chua/<ma>/du-bao/` | `/api/reservoirs/{code}/forecast/` |
| `/api/ho-chua/<ma>/lich-su/?tu=&den=` | `/api/reservoirs/{code}/history/?from=&to=` |
| `/api/canh-bao/`, `/api/thong-bao/` | `/api/alerts/`, `/api/notifications/` |

### App, model, trường

| Đặc tả | Code |
|---|---|
| PhuongXa | `catalog.Ward` |
| DoiCuuHo | `catalog.RescueTeam` |
| NguoiDung | `accounts.User` |
| CauHinh | `core.SystemConfig` |
| NhatKy | `core.AuditLog` |
| app "hochua" | apps `reservoirs` (hồ, số liệu, dự báo, ngưỡng) và `alerts` (cảnh báo, thông báo) |
| HoChua: ma, ten, mndbt, vi_do, kinh_do | `reservoirs.Reservoir`: code (av/dm/sb/st), name, normal_water_level, latitude, longitude; thêm `model_key` (tên hồ trong `du_bao`) |
| LienKetHoPhuongXa: ho, phuong_xa, loai_vung, can_xac_minh | `ReservoirWard`: reservoir, ward, zone, needs_verification |
| loai_vung khu_vuc_dap / ha_du_gan / ha_du_dong_bang | `dam_area` / `near_downstream` / `delta_downstream` |
| SoLieuVanHanh: thoi_gian, muc_nuoc, q_den, q_may, q_tran, nghi_ngo | `OperationRecord`: time, water_level, inflow, turbine_flow, spillway_flow, suspicious |
| LuongMua: thoi_gian, mua_mm, nguon | `Rainfall`: time, rain_mm, source (`historical` / `forecast`) |
| KetQuaDuBao: thoi_diem_du_bao, tam, muc_nuoc_du_kien, muc_canh_bao, baseline_bao, a_bao, b_bao, can_xac_nhan, phien_ban_mo_hinh, la_mo_phong, chi_tiet | `Forecast`: issued_at, horizon, expected_level, alert_level, baseline_alert, a_alert, b_alert, needs_confirmation, model_version, is_simulation, details |
| NguongQuyDinh: loai, tu_ngay, den_ngay, gia_tri_thap, gia_tri_cao, van_ban | `RegulatoryThreshold`: kind, start_day, end_day, value_low, value_high, document |
| loai cao_nhat_truoc_lu / don_lu_thap_nhat | `max_before_flood` / `min_flood_reception` |
| ChiDaoDieuHanh: loai_yeu_cau, muc_nuoc_muc_tieu, bat_dau, han_hoan_thanh, van_ban, con_hieu_luc, nguoi_nhap | `OperatingDirective`: requirement, target_level, starts_at, deadline, document, is_active, entered_by |
| loai_yeu_cau khong_vuot / ha_ve | `not_exceed` / `lower_to` |
| CanhBao: muc, nguon, noi_dung, bat_dau, hieu_luc_den, ket_thuc_luc, nguoi_phat, ket_qua_du_bao, la_mo_phong, hồ, phường/xã | `alerts.Alert`: level, source, content, starts_at, valid_until, ended_at, issued_by, forecast, is_simulation, reservoirs, wards |
| muc theo_doi / canh_bao / khan_cap; nguon tu_dong / thu_cong | `watch` / `warning` / `emergency`; `auto` / `manual` |
| Mức của `du_bao()`: binh_thuong / theo_doi / canh_bao | `AlertLevel`: `normal` / `watch` / `warning` (chỉ đổi tên, không tính lại) |
| ThongBao: nguoi_nhan, canh_bao, kenh, noi_dung, da_gui, da_xem_luc | `alerts.Notification`: recipient, alert, channel (`web` / `email`), content, sent, seen_at |
| (không có trong đặc tả) | `alerts.AlertState`: mức gần nhất của mỗi hồ, để xét "mức tăng" |
| LanCapNhat: bat_dau, ket_thuc, buoc, thanh_cong, loi | `reservoirs.UpdateRun`: started_at, finished_at, step, success, error |

### Lệnh quản trị, tham số

| Đặc tả | Code |
|---|---|
| nạp phường/xã | `load_wards` |
| tao_du_lieu_mau | `seed_demo_data` |
| nạp dữ liệu nền (4 hồ, ngưỡng, chỉ đạo, Phụ lục B) | `load_reservoirs` |
| nap_lich_su | `load_history` |
| bù mưa sau dữ liệu huấn luyện | `fetch_rain_history` |
| cap_nhat_du_bao | `update_forecasts` |
| phat_lai --tu --den | `replay_forecasts --from --to` |
| CauHinh chu_ky_tai_lai_tong_quan | `SystemConfig` `overview_refresh_minutes` |

## 8. Ghi chú bảo mật

- `.env` không được commit (đã có trong `.gitignore`); chỉ commit `.env.example`. `kho_du_lieu/` cũng không được commit.
- Mật khẩu băm bằng thuật toán mặc định của Django. Link xác thực và link đặt lại mật khẩu chỉ lưu dạng băm sha256, dùng một lần và có hạn.
- Khi đổi hoặc đặt lại mật khẩu, khoá tài khoản, đổi vai trò, mọi token cũ bị vô hiệu ngay: refresh token vào danh sách đen, còn access token bị từ chối nhờ số phiên bản ghi trong token.
- Đăng nhập sai quá số lần cho phép thì tài khoản bị tạm khoá. Tài khoản có tồn tại hay không đều bị khoá giống nhau, nên thông báo không tiết lộ tài khoản có tồn tại.
- Nhật ký hệ thống chỉ được thêm, được bảo vệ ở bốn lớp: API không có thao tác sửa/xoá, trang Django admin chỉ cho xem, model chặn `save()`/`delete()`, và một trigger PostgreSQL chặn mọi lệnh UPDATE/DELETE.
- Chỉ đạo điều hành không xoá được: API không có sửa/xoá, model chặn `delete()`. Sửa ngưỡng, thêm chỉ đạo và đánh dấu chỉ đạo hết hiệu lực đều được ghi nhật ký.
- Mọi tham số (thời gian khoá, hạn link, thời hạn JWT, ngưỡng dữ liệu cũ, ...) nằm trong bảng SystemConfig; admin sửa được, không viết cứng trong code.
- `seed_demo_data` từ chối chạy khi `DJANGO_DEBUG=false`.
