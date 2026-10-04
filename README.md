# Hệ thống cảnh báo lũ và cứu hộ khẩn cấp Đà Nẵng

Website theo tài liệu đặc tả `docs/dac_ta_chuc_nang.md`, làm theo 5 giai đoạn (mục 8 của đặc tả).

**Trạng thái: đã xong Giai đoạn 1** (CN01–CN05 tài khoản, CN23 quản lý người dùng, CN28 nhật ký hệ thống).

```
water-level-da-nang/
├── backend/     Django + DRF + JWT, PostgreSQL
│   ├── config/      settings (đọc .env), urls
│   ├── accounts/    User, đăng ký/đăng nhập/xác thực email/mật khẩu, hồ sơ, quản lý người dùng
│   ├── catalog/     Ward (phường/xã), RescueTeam (đội cứu hộ, bản tối thiểu)
│   ├── core/        SystemConfig (tham số), AuditLog (nhật ký chỉ thêm)
│   └── data/wards.csv   94 đơn vị theo Nghị quyết 1659/NQ-UBTVQH15 (có ghi nguồn)
├── frontend/    React (Vite) + React Router + Leaflet
├── du_bao/      Module dự báo chép từ thư mục nghiên cứu (xem du_bao/NGUON.md), dùng từ giai đoạn 2
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
pip install -r requirements.txt

cp .env.example .env
# Mở .env để điền:
#   DJANGO_SECRET_KEY: tạo bằng lệnh
#       python -c "import secrets; print(secrets.token_urlsafe(50))"
#   DB_PASSWORD: mật khẩu của user water (Postgres.app cấu hình mặc định "trust"
#                trên localhost nên để trống vẫn kết nối được)

python manage.py migrate            # tạo bảng, nạp giá trị ban đầu của SystemConfig
python manage.py load_wards         # nạp 94 phường/xã/đặc khu (chạy lại nhiều lần không bị trùng)
python manage.py seed_demo_data     # DỮ LIỆU DEMO: in ra các tài khoản và mật khẩu mẫu
python manage.py runserver          # http://localhost:8000
```

Cần thêm một admin thật (không phải demo) thì chạy `python manage.py createsuperuser`, rồi nhập email, họ tên, số điện thoại và mật khẩu.

**Email:** khi phát triển, email (xác thực, đặt lại mật khẩu) được **in ra terminal** đang chạy `runserver`; mở đường dẫn trong đó để xác thực. Dùng SMTP thật thì sửa `EMAIL_BACKEND` và các biến `EMAIL_*` trong `.env`.

**Trang quản trị Django:** http://localhost:8000/django-admin/ (đăng nhập bằng tài khoản admin). Tại đây xem nhật ký hệ thống (chỉ xem) và sửa tham số cấu hình.

## 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env     # không bắt buộc, giá trị mặc định đã dùng được
npm run dev              # http://localhost:5173
```

Vite chuyển tiếp các request `/api` sang `http://localhost:8000`, nên phải chạy backend trước.

## 3. Tài khoản demo

`python manage.py seed_demo_data` tạo (mật khẩu chung: `Demo12345`, **chỉ để thử**):

| Vai trò | Email | Số điện thoại | Ghi chú |
|---|---|---|---|
| Admin | admin@demo.example.com | 0900000001 | |
| Đội cứu hộ | doi1@demo.example.com | 0900000011 | Đội Đại Lộc: xe cứu hộ, xe máy |
| Đội cứu hộ | doi2@demo.example.com | 0900000012 | Đội Hội An: ca nô, xe máy |
| Người dân | dan1@demo.example.com | 0900000021 | Xã Đại Lộc |
| Người dân | dan2@demo.example.com | 0900000022 | Xã Duy Xuyên |
| Người dân | dan3@demo.example.com | 0900000023 | Phường Hội An |

Đăng nhập bằng email **hoặc** số điện thoại. Sau khi đăng nhập: người dân về `/`, đội cứu hộ về `/rescue/tasks`, admin về `/admin`.

## 4. Chạy test

Django cần quyền tạo database tạm `test_water_level`. Cấp quyền một lần cho user `water`:

```bash
psql -h localhost -d postgres -c "ALTER ROLE water CREATEDB;"
```

Rồi chạy:

```bash
cd backend && source .venv/bin/activate
python manage.py test
```

(Không muốn cấp quyền thì chạy bằng một user có sẵn quyền đó, ví dụ `DB_USER=$(whoami) python manage.py test` với Postgres.app.)

## 5. API giai đoạn 1

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

## 6. Ghi chú bảo mật

- `.env` không được commit (đã có trong `.gitignore`); chỉ commit `.env.example`.
- Mật khẩu băm bằng thuật toán mặc định của Django. Link xác thực và link đặt lại mật khẩu chỉ lưu dạng băm sha256, dùng một lần và có hạn.
- Đổi hoặc đặt lại mật khẩu, khoá tài khoản, đổi vai trò: mọi token cũ bị vô hiệu ngay (refresh token vào danh sách đen; access token bị từ chối nhờ số phiên bản trong token).
- Đăng nhập sai quá số lần cho phép thì tạm khoá. Tài khoản có tồn tại hay không đều bị khoá giống nhau, nên thông báo không tiết lộ tài khoản có tồn tại.
- Nhật ký hệ thống chỉ được thêm: API không có thao tác sửa/xoá, trang Django admin chỉ cho xem, model chặn `save()`/`delete()`, và một trigger PostgreSQL chặn mọi lệnh UPDATE/DELETE.
- Mọi tham số (thời gian khoá, hạn link, thời hạn JWT, ...) nằm trong bảng SystemConfig; admin sửa được, không viết cứng trong code.
