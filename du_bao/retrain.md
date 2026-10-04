# Hướng dẫn huấn luyện lại mô hình dự báo mực nước 4 hồ

Áp dụng cho các hồ A Vương, Đăk Mi 4, Sông Bung 4 và Sông Tranh 2. Tài liệu này dành cho người vận hành hệ thống khi có dữ liệu mới.

## Các file trong hệ thống

| File | Vai trò |
|---|---|
| `xu_ly_du_lieu.py` | Quy trình đọc, làm sạch và tạo đặc trưng, cùng tham số mô hình. **Dùng chung** cho cả đánh giá, huấn luyện và dự báo. |
| `train_4_mo_hinh.py` | Đánh giá mô hình: chia train/test theo thời gian, sinh bảng và hình trong `ket_qua/`. |
| `train_final.py` | Huấn luyện bản chạy thật trên toàn bộ dữ liệu, ghi vào `models/final_*.joblib` và `models/metadata.json`. |
| `du_bao.py` | Hàm `du_bao(ho, du_lieu_gan_nhat)` mà hệ thống gọi mỗi giờ. |
| `test_du_bao.py` | Kiểm tra bộ lọc gai và mô phỏng chạy từng giờ. |
| `chay_moi_gio.py` | **Lệnh chạy mỗi giờ**: cập nhật dữ liệu hồ → lấy mưa mới → `ghi_nhan_du_bao.py`. In dòng cron mẫu: `python3 chay_moi_gio.py --in-cron`. |
| `cap_nhat_du_lieu_ho.py` | Lấy dữ liệu vận hành mới từ cổng PCTT (API JSON của chính trang) và ghép vào `kho_du_lieu/van_hanh/van_hanh.csv`. Chỉ thêm giờ mới, không ghi đè. |
| `kho_du_lieu/` | Kho dữ liệu chạy thật. `van_hanh/van_hanh.csv` và `van_hanh/tho/*.json` (JSON gốc của mỗi lần lấy); `mua/mua_forecast_<hồ>.csv` (mưa Forecast đã lấy). |
| `ghi_nhan_du_bao.py` | Chạy mỗi giờ: lấy dữ liệu mới nhất, gọi `du_bao()` cho 4 hồ, ghi thêm vào `ket_qua/nhat_ky_du_bao.csv`. Không huấn luyện lại. |
| `nguon_mua.py` | Lấy mưa giờ từ Open-Meteo, lấy trung bình các điểm trong `models/toa_do_mua.json`. |
| `so_sanh_nguon_mua.py` | So sánh mưa giữa Open-Meteo Forecast API và Historical API. |
| `models/toa_do_mua.json` | Tọa độ các điểm lấy mưa của từng hồ. Phải giống hệt các điểm đã dùng lúc huấn luyện. |
| `ngoai_le_thu_cong.csv` | Danh sách các đoạn dữ liệu lỗi đã kiểm tra bằng tay và loại bỏ. |
| `models/nguong_van_hanh.json` | Ngưỡng vận hành của từng hồ: MNDBT, mực nước cao nhất trước lũ, mực nước đón lũ. |
| `requirements.txt` | Phiên bản thư viện đã dùng. |

## Khi nào cần huấn luyện lại

- **Sau mỗi mùa lũ** (khuyến nghị cuối tháng 12), khi đã có thêm một mùa dữ liệu.
- **Khi nâng cấp scikit-learn hoặc xgboost.** `du_bao.py` sẽ cảnh báo nếu phiên bản thư viện khác lúc huấn luyện.
- **Khi thêm dòng vào `ngoai_le_thu_cong.csv`** hoặc sửa dữ liệu lịch sử.
- **Khi sửa `xu_ly_du_lieu.py`.** Trường hợp này phải chạy lại cả bước đánh giá (bước 3), không chỉ bước 4.

Sửa `models/nguong_van_hanh.json` **không** cần huấn luyện lại; thay đổi có hiệu lực ở lần gọi tiếp theo, sau khi khởi động lại tiến trình.

## Quy trình

### 0. Chuẩn bị môi trường (chỉ làm lần đầu)

```bash
pip install -r requirements.txt
brew install libomp        # chỉ trên macOS: XGBoost cần thư viện OpenMP
```

### 1. Sao lưu mô hình đang chạy

```bash
cp -r models models_$(date +%Y%m%d)
```

Nếu mô hình mới kém hơn, chép thư mục sao lưu này trở lại `models/` là khôi phục được.

### 2. Cập nhật dữ liệu

> Khi hệ thống đã chạy hằng giờ, dữ liệu vận hành mới nằm sẵn trong `kho_du_lieu/van_hanh/van_hanh.csv`. Kho này có cùng định dạng với kết quả `doc_du_lieu_tho()`. Đến kỳ huấn luyện lại tới, nên chuyển `xu_ly_du_lieu.nap_du_lieu_sach()` sang đọc từ kho, thay vì xuất lại file `.xls`.

- **Dữ liệu vận hành:** xuất lại từ cổng PCTT và ghi đè `vanhanhthuydien.xls`. File này thực chất là HTML; script đã tự xử lý.
- **Dữ liệu mưa:** cập nhật 4 file `mua_data/mua_<hồ>.csv`, gồm các cột `thoi_gian` và `mua_mm`, mã hóa utf-8-sig.
- **Chú ý mốc kết thúc của dữ liệu mưa.** Các file mưa hiện chỉ có đến 31/12/2025, nên mọi dữ liệu vận hành sau ngày đó **không được dùng**: thiếu mưa thì không tạo được đặc trưng. Hãy kiểm tra dòng `Ghép mưa ...: x/y giờ có mưa` trong kết quả in ra.

### 3. Kiểm tra dữ liệu và đánh giá lại

1. Trong `train_4_mo_hinh.py`, đổi `NGAY_TEST` thành ngày bắt đầu mùa lũ gần nhất. Tập test nên chứa trọn một mùa lũ, ví dụ `"2026-08-01"`.
2. Chạy:
   ```bash
   python3 train_4_mo_hinh.py
   ```
3. Đọc phần làm sạch trong kết quả in ra:
   - **`Lọc gai mực nước`:** xem các ví dụ đã bị loại có đúng là lỗi nhập liệu không.
   - **`Bước nhảy mực nước > 1 m trong 1 giờ còn sót lại`:** mỗi dòng ở đây phải được kiểm tra bằng tay.
     - In mực nước và lưu lượng đến, qua máy, qua tràn từ 12 giờ trước đến 12 giờ sau mốc đó.
     - Nếu mực nước đổi mạnh mà lưu lượng xả không đổi tương ứng thì đó là lỗi. Thêm một dòng vào `ngoai_le_thu_cong.csv` gồm `ho, bat_dau, ket_thuc, ly_do`, rồi chạy lại.
4. So sánh kết quả với lần đánh giá trước:
   - `ket_qua/phan_loai.csv`: so F1 của Baseline, `Hồi quy → cảnh báo` (A) và `Baseline HOẶC XGBoost` (B).
   - `ket_qua/bootstrap_f1.csv`: nếu chênh lệch A − Baseline hoặc B − Baseline có khoảng tin cậy **nằm hẳn dưới 0**, phương án đó đang kém hơn Baseline. Cần xem xét trước khi đưa vào sử dụng.
   - Tầm nào được ghi "không đủ dữ liệu" thì `du_bao.py` sẽ tự bỏ XGBoost ở tầm đó (xem bước 4).

### 4. Huấn luyện bản cuối

1. Trong `train_final.py`, đặt `NGAY_TEST_DANH_GIA` **bằng đúng** giá trị `NGAY_TEST` vừa dùng ở bước 3. Giá trị này chỉ dùng để đánh dấu mô hình nào đã được đánh giá đủ dữ liệu.
2. Chạy:
   ```bash
   python3 train_final.py
   ```
3. Kiểm tra `models/metadata.json`:
   - `du_lieu_tu` / `du_lieu_den`: phải bao gồm phần dữ liệu mới.
   - `so_ca_duong`: số ca dâng nhanh của từng hồ và tầm.
   - `da_danh_gia: false`: với những tầm này, `du_bao.py` không dùng XGBoost và B chỉ dựa vào Baseline. Hiện tại đây là trường hợp Sông Bung 4 tầm 1h.
   - `phien_ban`: phiên bản thư viện, phải khớp với môi trường chạy hệ thống.

### 5. Kiểm tra trước khi đưa vào chạy thật

1. Trong `test_du_bao.py`, đổi `TU` và `DEN` sang một tháng có lũ gần đây.
2. Chạy:
   ```bash
   python3 test_du_bao.py
   ```
3. Kiểm tra kết quả:
   - **Phần 1** phải in đủ 4 dấu ✓. Nếu có `AssertionError`, nghĩa là bộ lọc gai thời gian thực đang hoạt động sai: **không được** đưa vào chạy thật.
     - Kiểm tra (d) dùng bản ghi lỗi thật lúc 25/10/2025 08:00 của A Vương, nên dữ liệu phải còn chứa mốc này.
   - **Phần 2** là mô phỏng. Vì mô hình đã thấy dữ liệu của tháng mô phỏng, phần này chỉ để xem hệ thống hoạt động hợp lý (báo trước các đợt dâng, không báo dày đặc khi không có lũ). **Không** dùng các số này làm kết quả đánh giá.
   - Mở `ket_qua/mo_phong_thang_10_2025.png` để xem trực quan.

### 6. Triển khai

Chép các file sau sang máy chạy hệ thống, dùng đúng phiên bản thư viện trong `requirements.txt`:

```
du_bao.py
xu_ly_du_lieu.py
ghi_nhan_du_bao.py
nguon_mua.py
models/nguong_van_hanh.json
models/toa_do_mua.json
models/metadata.json
models/final_hoi_quy_*.joblib   (12 file)
models/final_xgb_*.joblib       (12 file)
```

Đặt lịch chạy `ghi_nhan_du_bao.py` mỗi giờ; dòng cron mẫu có ở đầu file. Script này **không** tự tải dữ liệu vận hành: cần một bước khác cập nhật file xuất từ cổng PCTT trước mỗi lần chạy. Nếu bản ghi mới nhất cũ hơn 2 giờ, mỗi dòng nhật ký sẽ ghi cảnh báo trong cột `canh_bao_he_thong`.

Nhật ký `ket_qua/nhat_ky_du_bao.csv` chỉ được ghi thêm, không bao giờ sửa dòng cũ. Nếu danh sách cột thay đổi (ví dụ sau khi nâng cấp `du_bao.py`), script sẽ dừng thay vì ghi lệch cột. Khi đó hãy trỏ `--nhat-ky` sang một file mới và giữ nguyên file cũ.

Khi nạp, `du_bao.py` kiểm tra mã sha256 của từng file mô hình so với `metadata.json`. Nếu file bị chép thiếu hoặc lẫn phiên bản, hàm sẽ báo lỗi ngay thay vì chạy với mô hình sai.

## Những điều cần biết khi vận hành

- **Định dạng đầu vào.** Hàm `du_bao(ho, du_lieu_gan_nhat)` nhận các cột `mn, den, may, tran, mua`, theo giờ, ít nhất 170 giờ gần nhất. Dòng cuối là giờ hiện tại.
- **Mức cảnh báo.** `canh_bao` khi Baseline hoặc A báo; `theo_doi` khi chỉ có B báo; nếu trùng thì lấy mức cao hơn. A chỉ có ở tầm 1h và 3h.
- **Thiếu bản ghi giờ mới nhất.** Hàm không dự báo được (các trường trả về `None`) và ghi lý do vào `canh_bao_du_lieu`. Hàm cố ý không tự điền giá trị, vì lúc huấn luyện cũng không làm vậy. Trong mô phỏng tháng 10/2025, Sông Bung 4 có 7 giờ như vậy.
- **Bộ lọc gai thời gian thực.**
  - Nếu mực nước mới nhất lệch hơn 0,8 m so với giờ trước, cả bản ghi vận hành của giờ đó bị coi là nghi ngờ. Hệ thống tạm dùng mực nước và lưu lượng của giờ trước để tính.
  - Khi đó kết quả có `can_xac_nhan = True` kèm `ly_do_can_xac_nhan`, và `muc_canh_bao` **tối thiểu là `theo_doi`** để người trực kiểm tra trực tiếp.
  - Một giá trị nghi ngờ **không bao giờ** tự nó đẩy mức lên `canh_bao`. Nếu kết quả vẫn là `canh_bao`, mức đó đến từ diễn biến trước đó (ví dụ đang có lũ thật). Trường `muc_canh_bao_tu_mo_hinh` cho biết mức mà mô hình tính được trước khi áp mức tối thiểu `theo_doi`.
  - Giờ tiếp theo sẽ tự xác nhận: nếu mực nước quay về mức cũ thì giá trị đó bị loại là gai; nếu giữ mức mới thì được chấp nhận là thay đổi thật.
  - Hệ quả: một lần dâng thật nhanh hơn 0,8 m/giờ sẽ bị **cảnh báo chậm 1 giờ**. Trong dữ liệu 6/2024–12/2025 đã có 3 lần như vậy: A Vương 0,91 m, Đăk Mi 4 0,88 m, Sông Tranh 2 0,82 m.
- **Ngưỡng vận hành.** `models/nguong_van_hanh.json` lấy theo bảng quy định mực nước vận hành trên cổng PCTT Đà Nẵng (Quyết định 1865/QĐ-TTg).
  - Mực nước cao nhất trước lũ và mực nước đón lũ **chưa có khoảng ngày áp dụng** (đang ghi `can_xac_nhan_theo_QD1865`). Trong thời gian đó, `du_bao.py` vẫn so sánh, nhưng ghi `khoang_ap_dung_da_xac_nhan: false`.
  - Khi điền `tu`/`den` (dạng MM-DD), ngưỡng chỉ được áp dụng trong khoảng ngày đó. Ngoài khoảng, `nguong_m` trả về `null`.
- **Nguồn mưa khi chạy thật.**
  - Lúc huấn luyện, mưa lấy từ dữ liệu lịch sử. Khi chạy thật, `ghi_nhan_du_bao.py` lấy mưa từ Open-Meteo **Forecast API**, vì Historical API có ERA5 trễ khoảng 5 ngày.
  - Chạy `so_sanh_nguon_mua.py` để đo mức chênh giữa hai nguồn, dùng `--historical-model` để chọn đúng model đã tạo dữ liệu huấn luyện.
  - Cả hai script cần `models/toa_do_mua.json` được điền đủ: A Vương 5 điểm, mỗi hồ còn lại 4 điểm.
- **Bản ghi trùng mốc giờ trong nguồn.**
  - Nguồn PCTT có nhiều bản ghi trùng: file `.xls` có 4.277 giờ có nhiều bản ghi.
  - Huấn luyện và kho dùng **cùng một hàm** là `xu_ly_du_lieu.bo_trung_moc_gio`. Với mỗi hồ, hàm chọn bản ghi có mực nước gần nhất với trung bình của giờ trước và giờ sau, lấy từ các giờ kề bên không mâu thuẫn. Nếu không xác định được, hoặc có nhiều bản cách đều, hàm giữ bản xuất hiện sau cùng.
  - Hàm lấy nguyên 4 cột vận hành của hồ từ cùng một bản ghi.
  - Nhật ký từng giờ được lưu ở `ket_qua/bo_trung_moc_gio.csv`.
  - Áp dụng từ 01/10/2026. Kết quả trước khi đổi quy tắc được giữ ở `ket_qua/truoc_doi_quy_tac_trung/`; bảng so sánh ở `ket_qua/so_sanh_quy_tac_trung*.csv`.
- **Kho dữ liệu chỉ ghi thêm.**
  - `cap_nhat_du_lieu_ho.py` dừng, **không ghi gì**, nếu trang hoặc API lỗi hay đổi cấu trúc: đổi thứ tự hồ, đổi danh sách mã hồ, mất API, thiếu trường, giá trị không phải số.
  - Nếu nguồn sửa giá trị của một giờ đã có trong kho, script chỉ báo số giờ khác, không sửa kho.
  - Khi cần dựng lại kho, chạy `--xay-lai-tu-tho`. Lệnh này dựng lại từ `.xls` cộng với JSON gốc, và giữ bản cũ làm sao lưu.
- **Vì sao không dùng Selenium hoặc Playwright.** Trang chặn phiên Chrome tự động hóa với thông báo "The URL you requested has been blocked". Nút "Export Excel" chỉ lưu lại bảng dựng từ API JSON công khai của trang, nên script gọi thẳng API đó bằng HTTP thường. Đã đối chiếu 864/864 ô khớp với file xuất.
- **Không sửa riêng `du_bao.py`.** Không sửa cách làm sạch hay tạo đặc trưng chỉ trong `du_bao.py`. Mọi thay đổi phải sửa trong `xu_ly_du_lieu.py` rồi làm lại từ bước 3.
