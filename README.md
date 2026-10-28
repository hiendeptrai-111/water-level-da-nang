# Hệ thống cảnh báo lũ và cứu hộ khẩn cấp Đà Nẵng

Website theo tài liệu đặc tả `docs/dac_ta_chuc_nang.md`, làm theo 5 giai đoạn (mục 8 của đặc tả).

**Trạng thái: đã xong Giai đoạn 1, 2, 3 và 4.**

- Giai đoạn 1: CN01–CN05 (tài khoản), CN23 (quản lý người dùng), CN28 (nhật ký hệ thống).
- Giai đoạn 2: CN06–CN10 (hồ chứa, dự báo, cảnh báo tự động), CN12 (lịch sử cảnh báo), CN24 (ngưỡng và chỉ đạo), CN27 (tình trạng dữ liệu và mô hình).
- Giai đoạn 3: CN13 (thời tiết theo phường/xã), CN14 (bản đồ mưa), CN25 (tọa độ và liên kết hồ – phường/xã).
- Giao diện: đã làm lại toàn bộ theo thiết kế đã chốt `docs/thiet_ke_trang_chu.html`, gồm chế độ Sáng/Tối, trang chủ có bản đồ đập và mặt cắt ngang đập (xem mục "Giao diện" ở phần 2).
- Giai đoạn 4: CN15–CN21 (SOS, theo dõi SOS, điều phối, gợi ý đội theo đường đi thực tế, nhiệm vụ đội cứu hộ, điểm ngập), CN26 (quản lý đội cứu hộ). Giai đoạn 5 chưa làm.

```
water-level-da-nang/
├── backend/     Django + DRF + JWT, PostgreSQL
│   ├── config/      settings (đọc .env), urls
│   ├── accounts/    User, đăng ký/đăng nhập/xác thực email/mật khẩu, hồ sơ, quản lý người dùng
│   ├── catalog/     Ward (phường/xã), RescueTeam (đội cứu hộ, bản tối thiểu)
│   ├── core/        SystemConfig (tham số), AuditLog (nhật ký chỉ thêm)
│   ├── reservoirs/  Hồ chứa, số liệu vận hành, mưa, dự báo, ngưỡng, chỉ đạo, quy trình mỗi giờ
│   ├── alerts/      Cảnh báo, thông báo, cảnh báo tự động (CN10)
│   ├── weather/     Thời tiết phường/xã (bảng lưu đệm Open-Meteo), API thời tiết và bản đồ mưa
│   ├── rescue/      SOS, lịch sử SOS, điểm ngập, điều phối, tính đường đi (OSMnx + NetworkX)
│   └── data/
│       ├── wards.csv                 94 đơn vị theo Nghị quyết 1659/NQ-UBTVQH15 (có ghi nguồn)
│       ├── ward_centroids.csv        tọa độ trung tâm, nguồn và độ tin cậy (OpenStreetMap, ODbL)
│       ├── ward_boundaries.geojson   ranh giới 93 phường/xã (đã giản lược ~20 m) cho bản đồ mưa
│       └── danang_boundary.geojson   ranh giới TP Đà Nẵng, dùng kiểm tra tọa độ
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
python manage.py load_ward_centroids  # tọa độ trung tâm từ data/ward_centroids.csv (chạy lại không bị trùng)
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
npm test                 # test phần tính toán mặt cắt đập và chế độ Sáng/Tối (node --test, không cần thư viện)
```

Vite chuyển tiếp các request `/api` sang `http://localhost:8000`, nên phải chạy backend trước.

### Giao diện (thiết kế đã chốt: `docs/thiet_ke_trang_chu.html`)

- **Màu:** hai bộ màu Sáng/Tối lấy đúng từ `THEMES` và `ALERT` trong file thiết kế (`src/theme/themes.js`), chuyển thành biến CSS `--t-*` và `--a-*` theo `html[data-theme]`. Màu mức cảnh báo luôn đi kèm chữ.
- **Font:** Be Vietnam Pro cho chữ, IBM Plex Mono cho số đo (Google Fonts).
- **Nút Sáng/Tối:** nằm trên thanh điều hướng; ở trang chủ thì nằm trong thanh trên của trang.
  - Mặc định 06:00–17:59 theo giờ máy là Sáng, ngoài giờ là Tối. Lựa chọn của người dùng được nhớ trong `localStorage` (khoá `wl.theme`, mọi lần đọc/ghi đều bọc try/catch).
  - Khi chuyển, màu đổi dần trong 0,7 giây; mặt trời/mặt trăng chạy 1,6 giây. Với `prefers-reduced-motion`, mọi hiệu ứng động bị tắt.
- **Bản đồ:** URL lớp nền đọc từ `.env`, mỗi chế độ một URL (`VITE_MAP_TILE_URL_LIGHT`, `VITE_MAP_TILE_URL_DARK`), kèm dòng công nhận nguồn `VITE_MAP_ATTRIBUTION`.
  - Mặc định dùng Stadia Maps (Alidade Smooth / Alidade Smooth Dark). Trên localhost không cần khoá; khi đưa lên tên miền thật phải tạo tài khoản miễn phí và khai báo tên miền (xem `.env.example`).
  - CARTO không dùng được vì nay bắt buộc API key. Server tile của openstreetmap.org không có kiểu tối, và trên máy phát triển đang bị chặn.
  - Vùng xem giới hạn quanh đất liền Đà Nẵng.
- **Mặt cắt đập (`src/dam/DamCrossSection.jsx`):** dùng ở trang chủ và trang chi tiết hồ. Phần tính toán nằm trong `src/dam/crossSection.js` (hàm thuần, có test), theo đúng `renderVals()` của thiết kế.

## 3. Tài khoản demo

`python manage.py seed_demo_data` tạo các tài khoản dưới đây. Mật khẩu chỉ để thử trên máy phát triển; lệnh từ chối chạy khi `DJANGO_DEBUG=false`.

| Vai trò | Email | Số điện thoại | Mật khẩu | Ghi chú |
|---|---|---|---|---|
| Admin | admin@demo.example.com | 0900000001 | `Demo12345` | |
| Đội cứu hộ | doi1@demo.example.com | 0900000011 | `Demo12345` | Đội Đại Lộc: xe cứu hộ, xe máy |
| Đội cứu hộ | doi2@demo.example.com | 0900000012 | `Demo12345` | Đội Hội An: ca nô, xe máy |
| Người dân | dan1@demo.example.com | 0900000021 | `Demo12345` | Xã Đại Lộc |
| Người dân | dan2@demo.example.com | 0900000022 | `Demo12345` | Xã Duy Xuyên |
| Người dân | dan3@demo.example.com | 0900000023 | `Demo12345` | Phường Hội An |

Đăng nhập bằng email **hoặc** số điện thoại. Sau khi đăng nhập: người dân về `/`, đội cứu hộ về `/rescue/tasks`, admin về `/admin`.

Tài khoản bạn tự đăng ký hoặc tạo bằng `createsuperuser` không có trong bảng này. Mật khẩu chỉ lưu dạng băm nên không xem lại được; quên thì dùng "Quên mật khẩu", hoặc nhờ admin đặt lại ở trang Người dùng.

### Thử nhanh theo vai trò

- **Chưa đăng nhập:** vào `/sos`, nhập số điện thoại bất kỳ dạng `09xxxxxxxx`, nhấn giữ nút đỏ 3 giây. Ghi lại mã SOS để xem ở `/sos/track` (nhập mã cùng số điện thoại đã gửi).
- **Người dân** (`dan1@demo.example.com`): gửi SOS không cần nhập số điện thoại; xem ở menu "SOS của tôi"; báo điểm ngập ở `/flood-points/report` (cần admin duyệt).
- **Admin** (`admin@demo.example.com`): vào "Điều phối SOS" (`/admin/sos`), chọn một SOS, bấm "Tiếp nhận", "Gợi ý đội", rồi "Phân công". Duyệt điểm ngập ở `/admin/flood-points`.
- **Đội cứu hộ** (`doi1@demo.example.com`): ở `/rescue/tasks` thấy nhiệm vụ được giao. SOS chờ quá 15 phút chưa được phân công sẽ hiện ở mục "SOS chờ nhận"; số điện thoại chỉ hiện sau khi bấm "Nhận".

**SOS demo:** 3 SOS mô phỏng, số điện thoại `0900000101`, `0900000102`, `0900000103`. Mã SOS được tạo ngẫu nhiên mỗi lần chạy `seed_demo_data`; xem mã ở trang Điều phối SOS (đăng nhập admin). Dùng mã cùng số điện thoại tương ứng để xem ở `/sos/track`.

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

### Tọa độ đập và lưu lượng về hạ du

- **Tọa độ đập:** `python manage.py fetch_dam_coordinates` tìm các đối tượng `waterway=dam` tên "Đập thủy điện <hồ>" trong TP Đà Nẵng qua Overpass (1 request, lưu cache trong `kho_du_lieu/osm/`). Kết quả ghi vào `data/dam_coordinates.csv` (đã commit); `load_reservoirs` nạp file này.
  - Có trên OSM: A Vương (way 479648364), Sông Bung 4 (way 479647796), Đăk Mi 4 (way 439942289).
  - Sông Tranh 2: OSM không có đối tượng đập, chỉ có nhà máy và lòng hồ, nên dùng tọa độ gần đúng 15,34, 108,10 và đặt `coord_needs_verification = true`.
  - Admin sửa tọa độ đập trong trang quản trị Django: cờ cần xác minh được bỏ và có ghi AuditLog. Tọa độ admin đã sửa không bị `load_reservoirs` ghi đè.
- **Lưu lượng về hạ du:** "Q về Vu Gia" và "Q về Thu Bồn" lấy từ cột `q_vugia`, `q_thubon` của kho vận hành, lưu trong `RiverFlow` (nạp cùng `load_history` và lệnh chạy mỗi giờ). API `/api/reservoirs/` trả các giá trị này trong trường `river_flows`.

### Mưa

Mưa của một hồ là trung bình cộng các điểm trong `du_bao/models/toa_do_mua.json`. Cấu hình tải giống hệt lúc huấn luyện: `hourly=precipitation`, `timezone=Asia/Bangkok`, không chỉ định model. Mình đã kiểm tra: tải lại tuần 25–31/10/2025 bằng Archive API thì khớp dữ liệu huấn luyện 168/168 giờ.

Có hai nguồn, và mỗi giờ ghi rõ nguồn của nó (`Rainfall.source`):

- Đến (hôm nay − 5 ngày): lấy từ Historical API (`historical`).
- Phần gần đây hơn: lấy từ Forecast API, tham số `past_days` (`forecast`).

Khi cùng một giờ có cả hai nguồn, số liệu Historical luôn được ưu tiên.

### Lệnh, theo thứ tự

```bash
cd backend && source .venv/bin/activate
python manage.py load_reservoirs      # 4 hồ (+ tọa độ đập), ngưỡng A.1/A.2, chỉ đạo ví dụ A.4 (đã hết hiệu lực), liên kết Phụ lục B
python manage.py load_history         # kho_du_lieu -> cơ sở dữ liệu, đánh dấu số liệu nghi ngờ (~40 giây)
python manage.py fetch_rain_history   # bù mưa sau 31/12/2025, rồi báo số giờ còn thiếu
python manage.py update_forecasts     # chạy 1 lần quy trình mỗi giờ (cả thời tiết phường/xã), in dòng cron mẫu
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

| `heavy_rain_threshold_mm` | 50 mm/24 giờ | Ngưỡng hiển thị "Mưa lớn" trên trang thời tiết (tham khảo, không phải cảnh báo chính thức) |

Hai khoá `rapid_rise_threshold_m` (0,3 m) và `suspicious_jump_threshold_m` (0,8 m) **chỉ xem được**: không sửa được qua API (trả 403) hay trang quản trị Django. Hai giá trị này gắn với mô hình đã huấn luyện; muốn đổi thì phải huấn luyện lại.

## 4b. Thời tiết (giai đoạn 3)

### Tọa độ trung tâm và ranh giới phường/xã

Lệnh `python manage.py fetch_ward_centroids` lấy tọa độ từ OpenStreetMap qua Overpass API:

- Chỉ dùng 3 request (ranh giới thành phố, các ranh giới `admin_level=6` trong thành phố, các điểm `place=*`), tối đa 1 request/giây, User-Agent ghi tên dự án.
- Phản hồi gốc lưu trong `kho_du_lieu/osm/`; chạy lại thì dùng bản đã lưu (`--refresh` để tải lại).
- Kết quả ghi vào `data/ward_centroids.csv` (đã commit, nên khi cài đặt không cần chạy lại lệnh này).

Mỗi đơn vị có cột nguồn và độ tin cậy:

| Độ tin cậy | Ý nghĩa |
|---|---|
| `boundary` | Có ranh giới mới (`admin_level=6`, theo đơn vị hành chính từ 01/7/2025) khớp đúng tên; lấy trọng tâm diện tích của ranh giới. Nếu trọng tâm rơi ra ngoài ranh giới (hình lõm) thì dùng điểm nhãn của relation. |
| `needs_check` | Chỉ tìm được điểm cùng tên: "cần kiểm tra". |
| `missing` | Không tìm được: để trống. |
| `manual` | Admin đã nhập tay. Lệnh nạp lại không ghi đè (trừ khi có `--overwrite-manual`). |

Mọi tọa độ đều được kiểm tra nằm trong ranh giới TP Đà Nẵng; điểm nào nằm ngoài thì bị bỏ. Kết quả hiện tại: 93 `boundary`, 1 `missing` (đặc khu Hoàng Sa). Nominatim không dùng được vì trên máy phát triển, tên miền của nó bị chặn (phân giải về 127.0.0.1).

### Thời tiết theo giờ

`python manage.py update_weather` lấy dữ liệu từ Open-Meteo Forecast API:

- Các biến `temperature_2m`, `precipitation`, `wind_speed_10m`, với `past_days=1`, `forecast_days=4`, `timezone=Asia/Bangkok`.
- Mọi đơn vị có tọa độ được gom vào **một request**. Tài liệu Open-Meteo (https://open-meteo.com/en/docs) ghi: "Multiple coordinates can be comma separated … the JSON output changes to a list of structures". Theo cách tính giới hạn miễn phí, mỗi vị trí vẫn tính là một lần gọi (93 × 24 lần/ngày).
- Các giờ đến giờ hiện tại lưu với `kind=observed`, các giờ sau (tối đa 72 giờ) lưu với `kind=forecast`. `precipitation` là lượng mưa của giờ trước mốc giờ đó.
- Toàn bộ dữ liệu được tải và kiểm tra xong rồi mới ghi, trong một transaction: nếu lỗi thì dữ liệu cũ giữ nguyên, lỗi được ghi vào `UpdateRun`.
- Đơn vị thiếu tọa độ được bỏ qua và liệt kê trong `UpdateRun`.

Lệnh `update_forecasts` (cùng một dòng cron) chạy bước thời tiết **sau** phần hồ chứa, trong một bước riêng, nên lỗi thời tiết không làm dừng phần dự báo hồ. Dùng `--skip-weather` để bỏ qua bước này.

### CN25 trong trang quản trị Django

- **Phường/xã:** sửa vĩ độ và kinh độ. Tọa độ phải nằm trong Đà Nẵng, được đánh dấu `manual`, và mỗi lần sửa ghi AuditLog. Liên kết hồ – phường/xã (loại vùng, cần xác minh) sửa ngay trên trang của phường/xã.
- **Liên kết hồ – phường/xã:** sửa loại vùng và cờ "cần xác minh" ngay trong danh sách; mọi thay đổi đều ghi AuditLog.

## 4c. SOS và điều phối cứu hộ (giai đoạn 4)

### Cài đặt mạng đường (một lần)

```bash
brew install osmium-tool                         # macOS; Linux: apt install osmium-tool
# Tải bản trích xuất OpenStreetMap Việt Nam (~330 MB) vào kho_du_lieu/osm/:
curl -L -o kho_du_lieu/osm/vietnam-latest.osm.pbf https://download.geofabrik.de/asia/vietnam-latest.osm.pbf
cd backend && python manage.py fetch_road_network     # dựng đồ thị, lưu kho_du_lieu/roads/drive_appendix_b.graphml
```

**Vì sao dùng file Geofabrik mà không dùng Overpass:** Overpass công khai (overpass-api.de) từ chối các truy vấn lớn tải mạng đường. Thông báo của họ ghi rõ endpoint này dành cho công cụ do người thao tác; dùng tự động hoặc khối lượng lớn thì phải chạy máy chủ riêng. Vì vậy mạng đường được dựng từ bản trích xuất OpenStreetMap của Geofabrik (cùng dữ liệu OSM, giấy phép ODbL):

1. osmium cắt vùng bao 32 phường/xã Phụ lục B và căn cứ các đội, nới thêm khoảng 2 km.
2. Chỉ giữ các loại đường cho xe; bỏ đường `access=private/no`, `motor_vehicle=no`, `motorcar=no`.
3. OSMnx dựng đồ thị và cắt đúng theo vùng.

Kết quả (file `vietnam-261015.osm.pbf`, ngày 15/10/2026): **25.354 nút, 62.721 cạnh, GraphML 36,3 MB**, dựng trong 80 giây. Lệnh chạy lại thì dùng GraphML đã có (`--refresh` để dựng lại).

### Tính thời gian tiếp cận (CN18)

Đường đi tính bằng **OSMnx + NetworkX** (Dijkstra trên đồ thị có trọng số), không dùng OSRM như đặc tả ghi. Lý do: cần chặn hoặc làm chậm tức thì các đoạn đường ngập.

- **Trọng số cạnh** = chiều dài / tốc độ theo loại đường. Tốc độ dưới đây là **giả định của đề tài**, không phải số đo, nằm trong `rescue/routing.py`:

  | Loại đường (OSM `highway`) | km/h |
  |---|---|
  | motorway / trunk / primary / secondary / tertiary | 80 / 60 / 50 / 40 / 35 |
  | *_link (theo thứ tự trên) | 40 / 35 / 30 / 25 / 20 |
  | unclassified / residential / road / living_street | 25 / 20 / 20 / 10 |
  | loại khác | 20 |

  Từ vị trí chính xác của SOS hoặc của đội tới nút đường gần nhất: tính theo đường thẳng, 15 km/h.
- **Điểm ngập ĐÃ DUYỆT, còn hạn** ảnh hưởng mọi cạnh có đoạn thẳng nằm trong bán kính `flood_point_radius_m` (50 m):
  - "Xe máy không qua được": thời gian nhân `flood_slowdown_factor` (3).
  - "Ô tô không qua được" và "Chỉ ca nô": xoá cạnh với đội đi đường bộ.
  - Đồ thị không bị sao chép: điểm ngập được áp vào hàm trọng số của Dijkstra.
- **Đội có ca nô:** thời gian = khoảng cách đường thẳng / `boat_speed_kmh` (20 km/h). Đây là giả định đơn giản (xem phần Giới hạn). Đội có cả ca nô và xe được tính theo phương án nhanh hơn.
- **Không còn đường:** ghi "Không tiếp cận được bằng đường bộ".
- **Vị trí của đội:** vị trí đội gửi lên khi mở trang Nhiệm vụ, nếu mới hơn `team_location_max_age_minutes` (30 phút); nếu không thì dùng căn cứ của đội.
- **Hiệu năng:** chỉ một lần Dijkstra từ SOS trên đồ thị đảo chiều cho mọi đội. Với 1 SOS và 5 đội trên đồ thị Phụ lục B, thời gian thực tế là **0,13–0,22 giây**. Nạp đồ thị mất 3,8 giây, một lần cho mỗi tiến trình.
- **Chỉ gợi ý 3 đội tốt nhất**, kèm thời gian và tuyến đường; admin tự bấm "Phân công". Lỗi tính đường không ảnh hưởng việc gửi SOS hay phân công: phân công vẫn được, chỉ không có tuyến.

### Điểm ưu tiên SOS (giả định của đề tài, `rescue/services.py`)

```
điểm = mức nước (ngang gối 10, ngang ngực 30, ngập tầng 1 45, phải lên mái 70)
     + nhóm cần ưu tiên (10 điểm mỗi nhóm, tối đa 30)
     + số người (2–4: 5, từ 5: 10)
     + thời gian chờ (1 điểm mỗi 3 phút, tối đa 20)
     + mức cảnh báo đang có ở phường/xã (Theo dõi 5, Cảnh báo 15, Khẩn cấp 25)
Mức: ≥ 60 Rất cao · 40–59 Cao · 20–39 Trung bình · < 20 Thấp
```

Điểm được tính lại khi SOS thay đổi, khi mở danh sách điều phối, và mỗi phút (`check_sos_claims`).

### Luồng SOS

- **Trạng thái:** Mới gửi → Đã tiếp nhận → Đang di chuyển → Đã cứu → Đóng. Ngoài ra có Huỷ (người gửi huỷ khi đã an toàn) và Không liên lạc được (đội báo).
- **Lịch sử:** mọi lần đổi trạng thái đều thêm một dòng `SOSHistory`; thống kê thời gian xử lý lấy từ bảng này. "Đã đến nơi" và "Trả lại nhiệm vụ" cũng được ghi vào lịch sử.
- **Gửi SOS (`/sos`):**
  - Không cần đăng nhập; chưa đăng nhập thì bắt buộc số điện thoại.
  - Gửi vị trí và số điện thoại trước; số người, nhóm ưu tiên, mức nước, ghi chú và ảnh gửi bổ sung sau.
  - Mỗi tài khoản hoặc số điện thoại chỉ có 1 SOS đang mở; gửi tiếp thì cập nhật SOS cũ.
  - Giới hạn `sos_rate_limit_per_hour` (10) lần mỗi giờ, đếm riêng theo thiết bị và theo IP.
  - Ảnh: 1 ảnh, nén phía trình duyệt; server kiểm tra dung lượng (`sos_photo_max_kb`) và loại tệp thật (JPEG/PNG/WebP).
- **Khoá thao tác:** "Tiếp nhận" (admin) và "Nhận" (đội) khoá dòng SOS trong database, nên 2 admin hoặc 2 đội không xử lý trùng. Đội chỉ nhận thêm khi đang Rảnh.
- **Đội tự nhận:** chỉ thấy SOS chờ quá `sos_self_claim_wait_minutes` (15 phút) mà chưa được phân công. Trước khi nhận, đội chỉ thấy vị trí, mức ưu tiên và thời gian chờ; số điện thoại chỉ hiện sau khi nhận.
- **Lệnh chạy mỗi phút `check_sos_claims`:**
  - báo các đội rảnh gần nhất (`claim_notify_teams`, 3 đội) qua Notification website và email, mỗi SOS một lần;
  - cập nhật điểm ưu tiên;
  - cho điểm ngập hết hạn.
- **Ẩn danh hoá:** lệnh chạy mỗi ngày `anonymize_sos` xử lý các SOS đã Đóng hoặc Huỷ quá `sos_anonymize_days` (90) ngày:
  - xoá số điện thoại, ảnh, ghi chú, người gửi, mã thiết bị, IP, tuyến đường;
  - đổi tọa độ thành tâm phường/xã;
  - giữ thời điểm, phường/xã, trạng thái, lịch sử, số người, nhóm, mức nước để thống kê.

Lệnh không tự bật cron. Dòng cron mẫu (`--print-cron`):

```
* * * * *  cd /đường/dẫn/backend && .venv/bin/python manage.py check_sos_claims >> logs/check_sos_claims.log 2>&1
30 2 * * * cd /đường/dẫn/backend && .venv/bin/python manage.py anonymize_sos >> logs/anonymize_sos.log 2>&1
```

### Điểm ngập (CN20, CN21)

- Người dân báo thì ở trạng thái Chờ duyệt; đội cứu hộ và admin báo thì dùng ngay.
- Điểm ngập tự hết hạn sau `flood_point_ttl_hours` (12 giờ). Đội hoặc admin có thể xác nhận lại để gia hạn.
- Admin duyệt, từ chối, sửa mức, gộp điểm gần nhau (trong vòng 300 m).
- Bản đồ công khai `/flood-points` chỉ hiện điểm đã duyệt, không kèm người báo.

### Quản lý đội cứu hộ (CN26)

Trang quản trị Django → Đội cứu hộ: tên, căn cứ (vĩ độ, kinh độ), số thành viên, số điện thoại, phương tiện, các phường/xã thường phụ trách, trạng thái.

### Tham số mới trong SystemConfig

| Khoá | Mặc định | Ý nghĩa |
|---|---|---|
| `flood_point_radius_m` | 50 m | Bán kính ảnh hưởng của điểm ngập |
| `flood_slowdown_factor` | 3 lần | Hệ số làm chậm khi "xe máy không qua được" |
| `flood_point_ttl_hours` | 12 giờ | Thời hạn điểm ngập |
| `boat_speed_kmh` | 20 km/h | Tốc độ ca nô (đường thẳng) |
| `sos_rate_limit_per_hour` | 10 lần/giờ | Giới hạn gửi SOS theo thiết bị và theo IP |
| `sos_photo_max_kb` | 2048 KB | Dung lượng ảnh tối đa |
| `team_location_max_age_minutes` | 30 phút | Vị trí đội cũ hơn thì tính từ căn cứ |
| `claim_notify_teams` | 3 đội | Số đội được báo khi SOS chờ quá lâu |
| `sos_self_claim_wait_minutes`, `sos_anonymize_days`, `dispatch_refresh_seconds` | 15 phút, 90 ngày, 30 giây | (đã có từ giai đoạn 1) |

### Giới hạn đã biết

- Tốc độ theo loại đường và tốc độ ca nô là giả định, chưa hiệu chỉnh bằng số liệu thực tế.
- Ca nô được tính theo đường thẳng, không xét lòng sông.
- Mạng đường lấy từ bản trích xuất OSM tại một thời điểm; muốn cập nhật thì tải file mới và chạy `fetch_road_network --refresh`.
- Điểm ngập ảnh hưởng theo đoạn thẳng giữa hai nút của cạnh, không theo hình dạng cong chi tiết của con đường.

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

Frontend: `cd frontend && npm test`.

Test giai đoạn 4 dùng một đồ thị đường nhỏ dựng sẵn (không cần file mạng đường).

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

Khi xem mô phỏng tại thời điểm `at`, các trường "hiệu lực đến" và "kết thúc lúc" của cảnh báo là giá trị tại `at` (lưu trong `Alert.validity_history`), không phải giá trị cuối cùng của cả đợt.

### Giai đoạn 3

| Phương thức, đường dẫn | Quyền | Chức năng |
|---|---|---|
| `GET /api/weather/wards/{id}/` | Công khai | Hiện tại (nhiệt độ, mưa giờ qua, gió), mưa 24 giờ qua và 24 giờ tới, mưa theo giờ 72 giờ tới, thời điểm cập nhật, `stale`, cờ "Mưa lớn" (CN13) |
| `GET /api/weather/map/?metric=past24h\|next24h` | Công khai | Mưa 24 giờ cho mọi đơn vị; đơn vị thiếu tọa độ nằm trong `missing_coordinates` (CN14) |
| `GET /api/weather/boundaries/` | Công khai | GeoJSON ranh giới phường/xã (OpenStreetMap, ODbL) |
| `PATCH /api/admin/wards/{id}/` | Admin | Sửa tọa độ trung tâm `{latitude, longitude}`: kiểm tra nằm trong Đà Nẵng, ghi AuditLog (CN25) |

### Giai đoạn 4

| Phương thức, đường dẫn | Quyền | Chức năng |
|---|---|---|
| `POST /api/sos/` | Công khai (chưa đăng nhập phải có `phone`), giới hạn tần suất | Gửi SOS (vị trí + số điện thoại); SOS đang mở thì cập nhật |
| `GET/PATCH /api/sos/{code}/` | Người gửi (tài khoản, hoặc mã + `phone`) | Theo dõi; bổ sung thông tin, cập nhật vị trí |
| `POST /api/sos/{code}/cancel/`, `POST /api/sos/{code}/photo/` | Người gửi | Huỷ khi đã an toàn; gửi 1 ảnh |
| `GET /api/sos/mine/` | Người dân | SOS của mình |
| `GET /api/dispatch/sos/?status=&ward=` | Admin | Danh sách SOS (sắp theo ưu tiên), đội, điểm ngập đã duyệt (CN17) |
| `GET /api/dispatch/sos/{id}/`, `.../photo/` | Admin | Chi tiết, lịch sử, ảnh |
| `GET /api/dispatch/sos/{id}/suggestions/` | Admin | 3 đội tốt nhất, thời gian, tuyến (CN18) |
| `POST /api/dispatch/sos/{id}/receive|assign|merge|close/` | Admin | Tiếp nhận (có khoá), phân công `{team}`, gộp `{into: mã}`, đóng |
| `GET /api/rescue/tasks/` | Đội cứu hộ | Nhiệm vụ được giao, SOS chờ nhận (không có số điện thoại) (CN19) |
| `POST /api/rescue/tasks/{id}/claim|arrived|rescued|unreachable|return/` | Đội cứu hộ | Nhận (có khoá), cập nhật, trả lại `{note}` |
| `POST /api/rescue/location/`, `POST /api/rescue/status/` | Đội cứu hộ | Gửi vị trí đội; đặt trạng thái Rảnh / Đang làm nhiệm vụ / Nghỉ |
| `GET /api/flood-points/` | Công khai | Điểm ngập đã duyệt, không kèm người báo |
| `POST /api/flood-points/`, `POST /api/flood-points/{id}/confirm/` | Đã đăng nhập; xác nhận lại: đội/admin | Báo điểm ngập (CN20); gia hạn |
| `GET /api/admin/flood-points/`, `POST .../{id}/approve|reject|level|merge/` | Admin | Duyệt điểm ngập (CN21) |

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
| CN06 Tổng quan hồ chứa, `/` | `GET /api/reservoirs/`, màn hình `/` (`HomePage`: bản đồ `DamMap`, danh sách hồ, mặt cắt `DamCrossSection`) |
| Mặt cắt ngang đập (thiết kế trang chủ) | `src/dam/DamCrossSection.jsx`, phần tính toán `src/dam/crossSection.js` |
| CN07 Chi tiết và dự báo, `/ho-chua/:ma` | `/api/reservoirs/{code}/`, `.../forecast/`, `.../history/`; màn hình `/reservoirs/:code` |
| CN08 Tải dữ liệu hồ chứa | `GET /api/admin/reservoirs/{code}/export/`, nút "Tải CSV" trên `/reservoirs/:code` (admin) |
| CN09 Cảnh báo khu vực, `/canh-bao` | `GET /api/alerts/`, màn hình `/alerts` |
| CN10 Cảnh báo tự động | `alerts.services.evaluate`; `/api/notifications/`; chuông thông báo (`NotificationBell`) |
| CN12 Lịch sử cảnh báo, `/admin/canh-bao` | `/api/admin/alerts/`, màn hình `/admin/alerts` |
| CN15 Gửi SOS, `/sos` | `POST /api/sos/`, màn hình `/sos` (`SOSPage`, nút `HoldButton`) |
| CN16 Theo dõi SOS của tôi, `/sos/cua-toi` | `/api/sos/mine/`, `/api/sos/{code}/`; màn hình `/sos/track` |
| CN17 Bản đồ và danh sách SOS, `/admin/sos` | `/api/dispatch/sos/`; màn hình `/admin/sos` (`DispatchPage`, bản đồ `OpsMap`) |
| CN18 Gợi ý và phân công đội | `/api/dispatch/sos/{id}/suggestions/`, `.../assign/`; `rescue/routing.py` (OSMnx + NetworkX, thay OSRM) |
| CN19 Nhiệm vụ và tự nhận SOS, `/cuu-ho/nhiem-vu` | `/api/rescue/tasks/`; màn hình `/rescue/tasks` |
| CN20 Báo điểm ngập, `/diem-ngap/bao-cao` | `POST /api/flood-points/`; màn hình `/flood-points/report`; bản đồ công khai `/flood-points` |
| CN21 Duyệt điểm ngập, `/admin/diem-ngap` | `/api/admin/flood-points/`; màn hình `/admin/flood-points` |
| CN26 Quản lý đội cứu hộ, `/admin/doi-cuu-ho` | Django admin `catalog.RescueTeam` |
| CN23 Quản lý người dùng, `/admin/nguoi-dung` | `/api/admin/users/`, màn hình `/admin/users` |
| CN13 Thời tiết theo phường/xã, `/thoi-tiet` | `GET /api/weather/wards/{id}/`, màn hình `/weather` (`?ward=`); ô thời tiết trên trang chủ (`WeatherTile`) |
| CN14 Bản đồ mưa, `/thoi-tiet/ban-do` | `GET /api/weather/map/`, `/api/weather/boundaries/`; màn hình `/weather/map` |
| CN25 Quản lý phường/xã hạ du (`/admin/danh-muc`) | Django admin: `catalog.Ward` (tọa độ, liên kết hồ – phường/xã), `reservoirs.ReservoirWard`; `PATCH /api/admin/wards/{id}/` |
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
| DoiCuuHo: so_thanh_vien, can_cu, trang_thai (ranh/dang_lam/nghi), vi_tri_hien_tai, khu_vuc_phu_trach | `catalog.RescueTeam`: member_count, base_name, base_latitude/base_longitude, status (`available`/`busy`/`off`), current_latitude/current_longitude, location_updated_at, service_wards |
| SOS: ma, nguoi_gui, so_dien_thoai, vi_do, kinh_do, do_chinh_xac, phuong_xa, so_nguoi, nhom_uu_tien, muc_nuoc, ghi_chu, anh, diem_uu_tien, trang_thai, doi, gop_vao, gui_luc, an_danh_luc | `rescue.SOS`: code, sender, phone, latitude, longitude, accuracy_m, ward, people_count, vulnerable_groups, water_level, note, photo, priority_score, status, team, merged_into, created_at, anonymized_at |
| trang_thai SOS: moi_gui / da_tiep_nhan / dang_di_chuyen / da_cuu / dong / huy / khong_lien_lac_duoc | `new` / `received` / `moving` / `rescued` / `closed` / `cancelled` / `unreachable` |
| LichSuSOS: tu_trang_thai, sang_trang_thai, nguoi_thuc_hien, ghi_chu, thoi_diem | `rescue.SOSHistory`: from_status, to_status, actor, note, time |
| DiemNgap: muc (di_lai_duoc/xe_may_khong_qua/o_to_khong_qua/chi_ca_no), anh, nguoi_bao, trang_thai (cho_duyet/da_duyet/tu_choi/het_han), nguoi_duyet, het_han_luc | `rescue.FloodPoint`: level (`passable`/`no_motorbike`/`no_car`/`boat_only`), photo, reporter, status (`pending`/`approved`/`rejected`/`expired`), approved_by, expires_at |
| NguoiDung | `accounts.User` |
| CauHinh | `core.SystemConfig` |
| NhatKy | `core.AuditLog` |
| app "hochua" | apps `reservoirs` (hồ, số liệu, dự báo, ngưỡng) và `alerts` (cảnh báo, thông báo) |
| HoChua: ma, ten, mndbt, vi_do, kinh_do (tọa độ đập), can_xac_minh | `reservoirs.Reservoir`: code (av/dm/sb/st), name, normal_water_level, latitude, longitude, coord_source, coord_needs_verification; thêm `model_key` (tên hồ trong `du_bao`) |
| Q về Vu Gia, Q về Thu Bồn | `reservoirs.RiverFlow`: time, vu_gia, thu_bon |
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
| LanCapNhat: bat_dau, ket_thuc, buoc, thanh_cong, loi | `reservoirs.UpdateRun`: started_at, finished_at, step, success, error (bước thời tiết: `weather`) |
| app thời tiết | app `weather` |
| ThoiTiet: phuong_xa, thoi_gian, loai (da_qua/du_bao), nhiet_do, luong_mua, gio, cap_nhat_luc | `weather.WeatherReading`: ward, time, kind (`observed`/`forecast`), temperature, precipitation, wind_speed, updated_at |
| Tọa độ trung tâm phường/xã: vi_do, kinh_do, nguồn, độ tin cậy | `catalog.Ward`: latitude, longitude, coord_source, coord_confidence (`boundary`/`needs_check`/`missing`/`manual`), coord_note, osm_id |

### Lệnh quản trị, tham số

| Đặc tả | Code |
|---|---|
| nạp phường/xã | `load_wards` |
| tao_du_lieu_mau | `seed_demo_data` |
| nạp dữ liệu nền (4 hồ, ngưỡng, chỉ đạo, Phụ lục B) | `load_reservoirs` |
| nap_lich_su | `load_history` |
| bù mưa sau dữ liệu huấn luyện | `fetch_rain_history` |
| cap_nhat_du_bao | `update_forecasts` (gồm cả bước thời tiết) |
| lấy tọa độ phường/xã từ OpenStreetMap | `fetch_ward_centroids` |
| lấy tọa độ đập từ OpenStreetMap | `fetch_dam_coordinates` |
| dựng mạng đường (OSMnx) | `fetch_road_network` |
| kiểm tra mốc 15 phút (chạy mỗi phút) | `check_sos_claims` |
| ẩn danh hoá SOS (chạy mỗi ngày) | `anonymize_sos` |
| nạp tọa độ phường/xã | `load_ward_centroids` |
| cập nhật thời tiết | `update_weather` |
| CauHinh ngưỡng "Mưa lớn" | `SystemConfig` `heavy_rain_threshold_mm` |
| phat_lai --tu --den | `replay_forecasts --from --to` |
| CauHinh chu_ky_tai_lai_tong_quan | `SystemConfig` `overview_refresh_minutes` |

## 8. Ghi chú bảo mật

- `.env` không được commit (đã có trong `.gitignore`); chỉ commit `.env.example`. `kho_du_lieu/` cũng không được commit.
- Sửa tọa độ phường/xã chỉ dành cho admin (API trả 403 cho người dân và đội cứu hộ), luôn được kiểm tra nằm trong Đà Nẵng và ghi AuditLog.
- Mật khẩu băm bằng thuật toán mặc định của Django. Link xác thực và link đặt lại mật khẩu chỉ lưu dạng băm sha256, dùng một lần và có hạn.
- Khi đổi hoặc đặt lại mật khẩu, khoá tài khoản, đổi vai trò, mọi token cũ bị vô hiệu ngay: refresh token vào danh sách đen, còn access token bị từ chối nhờ số phiên bản ghi trong token.
- Đăng nhập sai quá số lần cho phép thì tài khoản bị tạm khoá. Tài khoản có tồn tại hay không đều bị khoá giống nhau, nên thông báo không tiết lộ tài khoản có tồn tại.
- Nhật ký hệ thống chỉ được thêm, được bảo vệ ở bốn lớp: API không có thao tác sửa/xoá, trang Django admin chỉ cho xem, model chặn `save()`/`delete()`, và một trigger PostgreSQL chặn mọi lệnh UPDATE/DELETE.
- Chỉ đạo điều hành không xoá được: API không có sửa/xoá, model chặn `delete()`. Sửa ngưỡng, thêm chỉ đạo và đánh dấu chỉ đạo hết hiệu lực đều được ghi nhật ký.
- Mọi tham số (thời gian khoá, hạn link, thời hạn JWT, ngưỡng dữ liệu cũ, ...) nằm trong bảng SystemConfig; admin sửa được, không viết cứng trong code.
- `seed_demo_data` từ chối chạy khi `DJANGO_DEBUG=false`. Lệnh tạo thêm căn cứ cho 2 đội, 4 điểm ngập và 3 SOS mô phỏng ở các xã hạ du, tất cả đánh dấu demo.
- Số điện thoại người gửi SOS: chỉ admin và đội đã nhận SOS đó xem được. Ảnh SOS và ảnh điểm ngập không phải tệp công khai, chỉ tải qua API có kiểm tra quyền. Điểm ngập công khai không kèm người báo.
