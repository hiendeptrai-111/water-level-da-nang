# Nguồn của thư mục du_bao/

- **Chép từ:** `~/Documents/data/` (thư mục nghiên cứu, giữ nguyên, không sửa)
- **Ngày chép:** 04/10/2026
- **Cách chép:** sao chép (`cp -p`), không di chuyển. Các file được chép: `xu_ly_du_lieu.py`, `du_bao.py`,
  `cap_nhat_du_lieu_ho.py`, `requirements.txt`, `retrain.md` và toàn bộ `models/`.
- **Sửa đổi:** không có. Mọi đường dẫn trong code đều tính theo vị trí file (`Path(__file__).parent`), nên
  `models/` vẫn được tìm đúng ở vị trí mới mà không phải sửa gì. Nội dung từng file giống hệt bản gốc
  (đã so bằng `cmp`).
- **Chưa chép:** `kho_du_lieu/` (giai đoạn 2), `mua_data/`, `vanhanhthuydien.xls`, `ngoai_le_thu_cong.csv`
  (dữ liệu huấn luyện), các script huấn luyện/đánh giá (`train_final.py`, `train_4_mo_hinh.py`, `test_du_bao.py`, ...).

## Kiểm tra sau khi chép (04/10/2026)

1. **sha256 mô hình:** 24/24 file `final_*` khớp với `models/metadata.json`
   (`ngay_huan_luyen` = 2026-10-01 14:59:14). `du_bao.py` cũng tự kiểm tra lại khi nạp mô hình.
2. **5 kiểm tra (a)–(e)** của `test_du_bao.py` (phần 1: bộ lọc gai thời gian thực) chạy với module ở vị trí
   mới: đạt cả 5. Kết quả của 6 lần gọi `du_bao()` (xuất JSON) giống hệt từng byte với khi chạy module gốc.
   Dữ liệu đầu vào đọc (chỉ đọc) từ `~/Documents/data`.

Môi trường: Python 3.12.6, scikit-learn 1.6.1, xgboost 3.4.1, pandas 2.2.3, numpy 1.26.4, joblib 1.4.2
(khớp `phien_ban` trong metadata.json).

## Lưu ý khi import (giai đoạn 2)

Thư mục `du_bao/` chứa file `du_bao.py` trùng tên. Phải thêm **thư mục `du_bao/`** vào `sys.path`
(không phải thư mục gốc dự án) để `import du_bao` nạp đúng file `du_bao.py` và `import xu_ly_du_lieu` chạy được.

## sha256

| File | sha256 | Ghi chú |
|---|---|---|
| `xu_ly_du_lieu.py` | `71d74bd75fb4f657470cb7aaf60462e47f048182d3d2cfef4bcf57c3f3662d4f` | |
| `du_bao.py` | `7a17f9b77a6ca179f56feba6f4135dd3a743d6d701199a544f856cf4ebfa0db8` | |
| `cap_nhat_du_lieu_ho.py` | `3a664336b51692bcbd54771a6bb9231ada7398edbb8956037660ad96ecc7f55b` | |
| `requirements.txt` | `0f534d56798ebb1466c179e85ab8ddfde6948aef8e1cc1005bae200b7f29dc1c` | |
| `retrain.md` | `8be9f6bbc68d1a745628ab8b2920b70f2b3ee7a1e9d68964c44d46d73242b9b0` | |
| `models/final_hoi_quy_a_vuong_1h.joblib` | `458bcbaf937957f4b0e48d42e1a7296a030f848419aa27d9316e5a7a736eb254` | khớp metadata.json |
| `models/final_hoi_quy_a_vuong_3h.joblib` | `c0fe7a546fed753de655763396f28b5fb7a8a1e4aa00aff926138a1e655a3ed0` | khớp metadata.json |
| `models/final_hoi_quy_a_vuong_6h.joblib` | `22e3e35fb44b06816cca38282e99c406e7db84991b7a78e19b7b5e44271e1f65` | khớp metadata.json |
| `models/final_hoi_quy_dak_mi_4_1h.joblib` | `4b06c5f3d59ac946a510d278a19f660edbf0e6bfc619edcc1b3712e1b11c4b64` | khớp metadata.json |
| `models/final_hoi_quy_dak_mi_4_3h.joblib` | `a7fc715f82073f9c6261852a8c3a90ab29253e85ecddbf33f25ccf3a94f41b69` | khớp metadata.json |
| `models/final_hoi_quy_dak_mi_4_6h.joblib` | `17414c08044ae2bbd690152443a01d69b66112bf32ea0823eb468b3bd792e0b9` | khớp metadata.json |
| `models/final_hoi_quy_song_bung_4_1h.joblib` | `d6f493df308f95793d05ed48a3be1b4680e400afd3e821f9d460f7b8d167b0c1` | khớp metadata.json |
| `models/final_hoi_quy_song_bung_4_3h.joblib` | `cf7a4df0e2027cf2a45252f9d694ffb5cf48af8741234d91296f5e846852cebd` | khớp metadata.json |
| `models/final_hoi_quy_song_bung_4_6h.joblib` | `65dd07c6c854a7ac744fc2e829f1a6a1e8f30a9eb566c9b1157ef02d6fd4259b` | khớp metadata.json |
| `models/final_hoi_quy_song_tranh_2_1h.joblib` | `88cee4ee168163beb6e11c21b444e525f481f9eddf0ac00ea0b290b8c9a38a84` | khớp metadata.json |
| `models/final_hoi_quy_song_tranh_2_3h.joblib` | `782e9cfa5bbec7599a20aaf21372409356e8005b304999a4662348ef25695ae7` | khớp metadata.json |
| `models/final_hoi_quy_song_tranh_2_6h.joblib` | `c3150c26eb50c41435f52c142dbe90ad05f9c5a736e4ade71b5d47b91d1ce4fc` | khớp metadata.json |
| `models/final_xgb_a_vuong_1h.joblib` | `2d2fcac104ed86c9c91bbc22653b8eef4801322a232b816be774888b304c85fd` | khớp metadata.json |
| `models/final_xgb_a_vuong_3h.joblib` | `fbb6a316bb3bcbf10c09015a6c580231cb06c48050905e0d73fbcbf3079cbbd6` | khớp metadata.json |
| `models/final_xgb_a_vuong_6h.joblib` | `5e68813fe21b17103cf4442846154b7eb32238a67629ff09db6a39fb6ab60c29` | khớp metadata.json |
| `models/final_xgb_dak_mi_4_1h.joblib` | `04a91ccb3ef90c1bd50212c7ca083bb7fc4be23bd936190f98a77c67d28d4def` | khớp metadata.json |
| `models/final_xgb_dak_mi_4_3h.joblib` | `b3a3dafe527d2fda05b530638b590100106c5622d1077e7467af8f1346ef861a` | khớp metadata.json |
| `models/final_xgb_dak_mi_4_6h.joblib` | `daa44687cc3870f23aa9511f9157ab4dc5902ce13003c1c834349ad41f2068be` | khớp metadata.json |
| `models/final_xgb_song_bung_4_1h.joblib` | `f1e48e296b8f92cb7822c11a6081e1589940fd95a68935d9bfa0c3e47a5429ca` | khớp metadata.json |
| `models/final_xgb_song_bung_4_3h.joblib` | `0656887f2bca9125d6e548a974ff8234d4c18b5e2fa920bbc113f00c36b590fe` | khớp metadata.json |
| `models/final_xgb_song_bung_4_6h.joblib` | `3444500cf28a147111ac5e72657e8e27df8d9c411c759d63572c67b92ccd0ebd` | khớp metadata.json |
| `models/final_xgb_song_tranh_2_1h.joblib` | `e39280721f89bea766bfac771773ee235081bcabdf97ba39520efaac86f616a1` | khớp metadata.json |
| `models/final_xgb_song_tranh_2_3h.joblib` | `97771dd1af94471f09e025b54f1cdca135d04dfaf161f83d5c29d004e16ce018` | khớp metadata.json |
| `models/final_xgb_song_tranh_2_6h.joblib` | `00628050a0e3868e53f776c76d1eab0312e96bc03b6f726309d6471e847c8c5a` | khớp metadata.json |
| `models/metadata.json` | `14453de5e94d03e342624b6ba468891b2cd1891248fa458fda767ce14303db0e` | cấu hình |
| `models/nguong_van_hanh.json` | `39f6186dcfa651f98e94441757737911d44ad836748f75753138d97e769ca8cf` | cấu hình |
| `models/toa_do_mua.json` | `eb92851380bcfbab5b1eb088e2cd4801c37856e964ad9d652bc4dbb36c2a49ae` | cấu hình |
| `models/xgb_hoi_quy_a_vuong_3h.joblib` | `f728791618becd4c53229f1757569872399c003ebae1007a9e70f00e4d3a3301` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_hoi_quy_a_vuong_6h.joblib` | `f96d49d3735f2f12b869e8b9f3a6324ec242c75e93085ca87b9bf17fcea012ec` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_hoi_quy_dak_mi_4_3h.joblib` | `57aab4b2629c45b5b9c1a5a815b58b836a1d6a640c8fc970196ea703efc85681` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_hoi_quy_dak_mi_4_6h.joblib` | `47a60aecc6d819ac1aaf75b68daa1e8082bf93bd36225b3d4eba401b9f0128e1` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_hoi_quy_song_bung_4_3h.joblib` | `9a53707352836c5899a38b49fb02e7dd172f13bc6d592a1768ae859cf93cdc39` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_hoi_quy_song_bung_4_6h.joblib` | `dd5a4fa9c4e324210416f0a950907e1b029e043ef0c99756e710764ed35672c4` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_hoi_quy_song_tranh_2_3h.joblib` | `4921e25466879d4c3f80b78641b847468863259153f45a058cb6523064f760c9` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_hoi_quy_song_tranh_2_6h.joblib` | `92b6ec8ff4656b47208352f2223d35a5731a89b905d67a09f47d9416de992f6c` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_phan_loai_a_vuong_3h.joblib` | `54e13ca9e7753af97d30c3fb46011bc356438b13b8a25230a00618686a2c9fd8` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_phan_loai_a_vuong_6h.joblib` | `35644fcf2c3aa985c6e18408b440431e5827412d25ce873fea27f4b983034050` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_phan_loai_dak_mi_4_3h.joblib` | `67101c2e55b45a924e4c7773fdba4b9fa58e340045cd19b9a841266fcf136d9a` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_phan_loai_dak_mi_4_6h.joblib` | `30b4d9d1afada55ffc0c0bf4d563eaadf47d865549342313c49c1ead1a587a4c` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_phan_loai_song_bung_4_3h.joblib` | `7510d2f55b7fbb4cb3c8e7333d86861bbc78518aec974bd2b6299094d6be3a3f` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_phan_loai_song_bung_4_6h.joblib` | `ba87abaf9c35c3a7b0881bd7416267e257c0fdf2a9bb0ed04a9ce6418db6cf8b` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_phan_loai_song_tranh_2_3h.joblib` | `7ebbcd1f67e72ffd5fe5e948b1e6167845b27c48e60aa6faab50d3f06856eb45` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
| `models/xgb_phan_loai_song_tranh_2_6h.joblib` | `cd3bedf13004d5571d7f2254b14675099180174941e3d3ef0c71a7dee9c7f39d` | không có trong metadata (mô hình đánh giá, du_bao.py không nạp) |
