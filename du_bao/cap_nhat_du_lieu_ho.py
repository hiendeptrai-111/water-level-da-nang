"""Cập nhật kho dữ liệu vận hành 4 hồ từ cổng PCTT Đà Nẵng.

Trang "A Vương, SB4, ĐM4, ST2" (https://pctt.danang.gov.vn/so-lieu/thuy-đien/a-vuong-sb4-đm4-st2)
nạp bảng từ API JSON công khai của chính trang:
    /DesktopModules/PCTT/api/PCTTApi/baocaothuydiens_thongke?ngaybatdau=..&ngayketthuc=..&lst_thuydien_id=1,2,3,4
Nút "Export Excel" chỉ lưu lại bảng HTML dựng từ JSON này (vì vậy vanhanhthuydien.xls là HTML,
số làm tròn 2 chữ số). Script gọi thẳng API đó bằng HTTP thường — không cần trình duyệt.
(Đã thử Selenium/Chrome headless: trang chặn phiên trình duyệt tự động hoá với thông báo
"The URL you requested has been blocked"; script không tìm cách vượt qua việc chặn đó.)
Đã kiểm chứng 01/10/2026: 48 giờ (25–27/10/2025) × 18 cột lấy từ API khớp 864/864 ô với
vanhanhthuydien.xls.

Mỗi lần chạy:
  1. Kiểm tra trang còn đúng cấu trúc: còn gọi API trên, danh sách hồ = "1,2,3,4", thứ tự
     cột A Vương, Đăk Mi 4, Sông Bung 4, Sông Tranh 2. Sai -> dừng, không ghi gì.
  2. Lấy từ (mốc cuối trong kho − 6 giờ chồng lấn) đến hiện tại, chia đoạn 7 ngày.
     Mọi đoạn phải thành công và đúng cấu trúc thì mới ghi; một đoạn lỗi -> dừng, không ghi.
  3. Lưu nguyên văn JSON nhận được vào kho_du_lieu/van_hanh/tho/ (file mới, không ghi đè).
  4. Ghép vào kho_du_lieu/van_hanh/van_hanh.csv: chỉ thêm các giờ CHƯA có; giờ đã có giữ
     nguyên giá trị cũ (nếu nguồn đã sửa giá trị, chỉ báo số giờ khác, không sửa kho).
     Ghi kiểu nguyên tử: file tạm (nội dung cũ giữ nguyên từng byte + dòng mới) rồi thay thế.

Lần đầu:  python3 cap_nhat_du_lieu_ho.py --khoi-tao   (tạo kho từ vanhanhthuydien.xls)
Khôi phục: python3 cap_nhat_du_lieu_ho.py --xay-lai-tu-tho (dựng lại từ xls + JSON gốc, giữ bản cũ)
Hằng giờ: python3 cap_nhat_du_lieu_ho.py
Mã thoát: 0 = thành công (kể cả không có giờ mới), 1 = lỗi (kho không bị thay đổi).
"""
import argparse
import fcntl
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import xu_ly_du_lieu as xl
from xu_ly_du_lieu import COT

GOC = Path(__file__).resolve().parent
KHO = xl.F_KHO_VAN_HANH.parent
F_KHO = xl.F_KHO_VAN_HANH
THU_MUC_THO = KHO / "tho"
F_KHOA = KHO / ".dang_chay.lock"

URL_TRANG = "https://pctt.danang.gov.vn/so-lieu/thuy-%C4%91ien/a-vuong-sb4-%C4%91m4-st2"
URL_API = "https://pctt.danang.gov.vn/DesktopModules/PCTT/api/PCTTApi/baocaothuydiens_thongke"
DS_HO_API = "1,2,3,4"
TEN_HO_TRANG = ["A Vương", "Đăk Mi 4", "Sông Bung 4", "Sông Tranh 2"]
MUI_GIO = ZoneInfo("Asia/Ho_Chi_Minh")
LECH_UTC = timedelta(hours=7)        # API nhận ngày theo UTC ("...Z"), trả giờ địa phương
CHONG_LAN = timedelta(hours=6)
DOAN_NGAY = 7
NGHI_GIUA_YEU_CAU = 2.0              # giây, tránh gửi dồn dập
UA = "cap_nhat_du_lieu_ho/1.0 (python-urllib; du lieu van hanh ho, 1 lan/gio)"

# cột kho <- trường JSON (theo đoạn JavaScript dựng bảng trên trang)
ANH_XA = {}
for _p, _i in {"av": 1, "dm": 2, "sb": 3, "st": 4}.items():
    ANH_XA.update({f"{_p}_mn": f"htl{_i}", f"{_p}_den": f"qvao{_i}",
                   f"{_p}_may": f"luuluongnhamay{_i}", f"{_p}_tran": f"qxaquacua{_i}"})
ANH_XA.update({"q_vugia": "qvevugia", "q_thubon": "qvethubon"})
TRUONG_BAT_BUOC = {"thoigianxa", "ngay", "gio", *ANH_XA.values()}


class LoiNguon(RuntimeError):
    """Trang/API lỗi hoặc đổi cấu trúc — dừng, không ghi dữ liệu."""


def _get(url, thoi_gian_cho=60, so_lan=3):
    loi = None
    for lan in range(so_lan):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=thoi_gian_cho) as r:
                noi_dung = r.read().decode("utf-8")
            if "been blocked" in noi_dung[:2000]:
                raise LoiNguon(f"Trang trả về thông báo chặn truy cập: {url}")
            return noi_dung
        except LoiNguon:
            raise
        except Exception as e:   # lỗi mạng tạm thời -> thử lại
            loi = e
            time.sleep(5 * (lan + 1))
    raise LoiNguon(f"Không tải được {url} sau {so_lan} lần: {type(loi).__name__}: {loi}")


def kiem_tra_trang():
    """Phát hiện trang đổi cấu trúc trước khi tin dữ liệu API."""
    s = _get(URL_TRANG)
    loi = []
    if "PCTTApi/baocaothuydiens_thongke" not in s:
        loi.append("trang không còn gọi API baocaothuydiens_thongke")
    m = re.search(r'id="dnn_ctr\d+_View_lbl_lstNhaMay"[^>]*>(.*?)<', s, re.S)
    if not m or m.group(1).strip() != DS_HO_API:
        loi.append(f"danh sách hồ của trang là {m.group(1).strip() if m else '<không thấy>'}, "
                   f"mong đợi {DS_HO_API}")
    # HTML gốc (chưa qua DataTables): tên hồ nằm trực tiếp trong <th>
    tieu_de = [re.sub(r"<[^>]+>", "", t).strip()
               for t in re.findall(r"<th[^>]*>(.*?)</th>", s, re.S)]
    ho = [t.replace("Hồ thủy điện", "").strip() for t in tieu_de if t.startswith("Hồ thủy điện")]
    if ho[:4] != TEN_HO_TRANG:
        loi.append(f"thứ tự hồ trên trang là {ho[:4]}, mong đợi {TEN_HO_TRANG}")
    for truong in ["htl", "qvao", "luuluongnhamay", "qxaquacua", "qvevugia", "qvethubon"]:
        if f'"{truong}' not in s and f"'{truong}" not in s and truong not in s:
            loi.append(f"đoạn mã dựng bảng không còn trường '{truong}'")
    if loi:
        raise LoiNguon("Trang PCTT đã đổi cấu trúc: " + "; ".join(loi))


def goi_api(ngay_tu, ngay_den):
    """Lấy bản ghi có giờ địa phương trong [ngay_tu 00:00, ngay_den 23:00]."""
    a = (datetime.combine(ngay_tu, datetime.min.time()) - LECH_UTC)
    b = (datetime.combine(ngay_den, datetime.min.time()) + timedelta(hours=23) - LECH_UTC)
    q = urllib.parse.urlencode({"ngaybatdau": f"{a:%Y-%m-%dT%H:%M:%S}.000Z",
                                "ngayketthuc": f"{b:%Y-%m-%dT%H:%M:59}.000Z",
                                "lst_thuydien_id": DS_HO_API})
    url = f"{URL_API}?{q}"
    try:
        du_lieu = json.loads(_get(url))
    except json.JSONDecodeError as e:
        raise LoiNguon(f"API không trả JSON hợp lệ ({e}) — có thể đã đổi cấu trúc") from e
    if not isinstance(du_lieu, list):
        raise LoiNguon(f"API trả {type(du_lieu).__name__}, mong đợi danh sách bản ghi")
    for i, r in enumerate(du_lieu):
        thieu = TRUONG_BAT_BUOC - set(r)
        if thieu:
            raise LoiNguon(f"Bản ghi {i} thiếu trường {sorted(thieu)} — API đã đổi cấu trúc")
        for k in ANH_XA.values():
            if r[k] is not None and not isinstance(r[k], (int, float)):
                raise LoiNguon(f"Trường {k} = {r[k]!r} không phải số")
    return url, du_lieu


def chuyen_bang(ban_ghi):
    """JSON -> bảng như khi đọc file xuất (làm tròn 2 chữ số, bỏ trùng bằng xl.bo_trung_moc_gio)."""
    if not ban_ghi:
        return pd.DataFrame(columns=COT[2:], dtype=float)
    d = pd.DataFrame(ban_ghi)
    # Có bản ghi nhập giờ lẻ kèm phần giây (vd "2026-01-28T13:16:42.64"). File xuất dùng
    # ngay + gio (đến phút) rồi làm tròn về giờ -> làm y hệt; thoigianxa chỉ để đối chiếu.
    t = pd.to_datetime(d["thoigianxa"], format="ISO8601", errors="coerce")
    t_ngay_gio = pd.to_datetime(d["ngay"] + " " + d["gio"], format="%m/%d/%y %H:%M", errors="coerce")
    sai = t.isna() | t_ngay_gio.isna() | (t.dt.floor("min") != t_ngay_gio)
    if sai.any():
        vd = d.loc[sai, ["thoigianxa", "ngay", "gio"]].head(5).to_dict("records")
        raise LoiNguon(f"{int(sai.sum())} bản ghi có thoigianxa không đọc được hoặc không khớp "
                       f"ngay/gio — API có thể đã đổi định dạng. Ví dụ: {vd}")
    bang = d[list(ANH_XA.values())].rename(columns={v: k for k, v in ANH_XA.items()})
    bang = bang.astype(float).round(2)[COT[2:]]
    bang.insert(0, "thoi_gian", t_ngay_gio.dt.round("h"))
    # Bỏ trùng mốc giờ bằng ĐÚNG hàm dùng khi huấn luyện (xl.bo_trung_moc_gio), thứ tự dòng =
    # thứ tự API trả về (cũng là thứ tự dòng trong file Export Excel).
    ket_qua, _ = xl.bo_trung_moc_gio(bang)
    return ket_qua


def ghi_nguyen_tu(bang_moi):
    """Thêm dòng vào kho: file tạm = nội dung cũ (giữ nguyên từng byte) + dòng mới, rồi thay thế."""
    cu = F_KHO.read_bytes()
    them = bang_moi.reset_index()
    them["thoi_gian"] = them["thoi_gian"].dt.strftime("%Y-%m-%d %H:%M")
    noi_dung_moi = them.to_csv(index=False, header=False, lineterminator="\n",
                               float_format="%.2f").encode("utf-8")
    tam = F_KHO.with_suffix(".csv.tam")
    with open(tam, "wb") as f:
        f.write(cu if cu.endswith(b"\n") else cu + b"\n")
        f.write(noi_dung_moi)
        f.flush()
        os.fsync(f.fileno())
    if tam.read_bytes()[:len(cu)] != cu:
        tam.unlink()
        raise RuntimeError("Kiểm tra sau khi ghi tạm thất bại — không thay kho")
    os.replace(tam, F_KHO)


def khoi_tao():
    if F_KHO.exists():
        raise SystemExit(f"{F_KHO} đã tồn tại — không khởi tạo lại (không ghi đè dữ liệu cũ)")
    KHO.mkdir(parents=True, exist_ok=True)
    THU_MUC_THO.mkdir(exist_ok=True)
    tho = xl.doc_du_lieu_tho()
    bang = tho.reset_index()
    bang["thoi_gian"] = bang["thoi_gian"].dt.strftime("%Y-%m-%d %H:%M")
    tam = F_KHO.with_suffix(".csv.tam")
    bang.to_csv(tam, index=False, encoding="utf-8-sig", lineterminator="\n", float_format="%.2f")
    os.replace(tam, F_KHO)
    kiem = xl.doc_kho_van_hanh(in_ra=lambda *a: None)
    pd.testing.assert_frame_equal(kiem, tho.astype(float), check_names=False, check_freq=False)
    print(f"Đã khởi tạo kho từ {xl.tim_file('vanhanhthuydien.xls').name}: {len(tho):,} giờ "
          f"({tho.index.min()} → {tho.index.max()}), đọc lại khớp 100%")


def xay_lai_tu_tho():
    """Dựng lại kho từ vanhanhthuydien.xls + toàn bộ JSON gốc trong tho/ (theo thứ tự lần lấy,
    mỗi lần chỉ thêm giờ chưa có — đúng như cập nhật hằng giờ). Kho cũ được giữ lại thành
    file sao lưu, không xóa. Dùng khi kho hỏng hoặc khi đổi quy tắc xử lý."""
    tho = xl.doc_du_lieu_tho(in_ra=lambda *a: None).astype(float)
    bang = tho.copy()
    lan_lay = {}
    for f in sorted(THU_MUC_THO.glob("*.json")):
        lan_lay.setdefault(f.name[:15], []).append(f)          # tiền tố YYYYmmdd_HHMMSS
    for nhan, ds in sorted(lan_lay.items()):
        moi = chuyen_bang([r for f in ds for r in json.loads(f.read_text(encoding="utf-8"))["ban_ghi"]])
        bang = pd.concat([bang, moi.drop(index=moi.index.intersection(bang.index))]).sort_index()
    sao_luu = F_KHO.with_name(f"van_hanh_saoluu_{datetime.now(MUI_GIO):%Y%m%d_%H%M%S}.csv")
    os.replace(F_KHO, sao_luu)
    ra = bang.reset_index().rename(columns={"index": "thoi_gian"})
    ra["thoi_gian"] = ra["thoi_gian"].dt.strftime("%Y-%m-%d %H:%M")
    tam = F_KHO.with_suffix(".csv.tam")
    ra.to_csv(tam, index=False, encoding="utf-8-sig", lineterminator="\n", float_format="%.2f")
    os.replace(tam, F_KHO)
    cu = xl.doc_kho_van_hanh(sao_luu, in_ra=lambda *a: None)
    sau = xl.doc_kho_van_hanh(in_ra=lambda *a: None)
    c = cu.index.intersection(sau.index)
    khac = int((~np.isclose(cu.loc[c].values, sau.loc[c].values, atol=0.005, equal_nan=True)).any(axis=1).sum())
    print(f"Đã dựng lại kho từ xls + {len(lan_lay)} lần lấy: {len(sau):,} giờ, đến "
          f"{sau.index.max():%d/%m/%Y %H:%M}; {khac} giờ khác bản cũ; bản cũ lưu ở {sao_luu.name}")


def cap_nhat(den=None):
    if not F_KHO.exists():
        raise SystemExit(f"Chưa có kho {F_KHO}. Chạy trước: python3 cap_nhat_du_lieu_ho.py --khoi-tao")
    kho = xl.doc_kho_van_hanh(in_ra=lambda *a: None)
    bay_gio = datetime.now(MUI_GIO).replace(tzinfo=None, minute=0, second=0, microsecond=0)
    den = pd.Timestamp(den) if den else pd.Timestamp(bay_gio)
    tu = kho.index.max() - CHONG_LAN
    print(f"Kho có đến {kho.index.max():%d/%m/%Y %H:%M}; lấy {tu:%d/%m/%Y %H:%M} → {den:%d/%m/%Y %H:%M}")

    kiem_tra_trang()
    print("  Trang PCTT: cấu trúc đúng như mong đợi")

    # 1) tải toàn bộ các đoạn; lỗi ở bất kỳ đoạn nào -> dừng, chưa ghi gì
    doan, ngay = [], tu.date()
    while ngay <= den.date():
        ngay_cuoi = min(ngay + timedelta(days=DOAN_NGAY - 1), den.date())
        url, ban_ghi = goi_api(ngay, ngay_cuoi)
        doan.append((ngay, ngay_cuoi, url, ban_ghi))
        print(f"  API {ngay:%d/%m/%Y} → {ngay_cuoi:%d/%m/%Y}: {len(ban_ghi)} bản ghi")
        ngay = ngay_cuoi + timedelta(days=1)
        if ngay <= den.date():
            time.sleep(NGHI_GIUA_YEU_CAU)

    tat_ca = [r for *_, ban_ghi in doan for r in ban_ghi]
    moi = chuyen_bang(tat_ca)
    moi = moi[(moi.index >= tu) & (moi.index <= den)]
    da_co = moi.index.intersection(kho.index)
    khac = 0
    if len(da_co):
        a, b = moi.loc[da_co, COT[2:]].values, kho.loc[da_co, COT[2:]].values
        khac = int((~np.isclose(a, b, atol=0.005, equal_nan=True)).any(axis=1).sum())
    them = moi.drop(index=da_co).sort_index()

    # 2) lưu JSON gốc (file mới) rồi ghi kho kiểu nguyên tử
    THU_MUC_THO.mkdir(parents=True, exist_ok=True)
    nhan = datetime.now(MUI_GIO).strftime("%Y%m%d_%H%M%S")
    for ngay_dau, ngay_cuoi, url, ban_ghi in doan:
        f = THU_MUC_THO / f"{nhan}_{ngay_dau:%Y%m%d}_{ngay_cuoi:%Y%m%d}.json"
        with open(f, "x", encoding="utf-8") as fh:     # "x": không bao giờ ghi đè
            json.dump({"url": url, "lay_luc": nhan, "ban_ghi": ban_ghi}, fh, ensure_ascii=False)
    if len(them):
        ghi_nguyen_tu(them)
    print(f"  Thêm {len(them)} giờ mới"
          + (f" ({them.index.min():%d/%m/%Y %H:%M} → {them.index.max():%d/%m/%Y %H:%M})" if len(them) else "")
          + f"; {len(da_co)} giờ đã có (giữ nguyên)"
          + (f", trong đó {khac} giờ nguồn hiện có giá trị KHÁC kho — không sửa kho" if khac else ""))
    sau = xl.doc_kho_van_hanh(in_ra=lambda *a: None)
    print(f"  Kho sau cập nhật: {len(sau):,} giờ, đến {sau.index.max():%d/%m/%Y %H:%M}")
    return {"so_gio_moi": len(them), "moc_cuoi": sau.index.max(), "gio_khac_nguon": khac}


def main():
    ap = argparse.ArgumentParser(description="Cập nhật kho dữ liệu vận hành 4 hồ từ cổng PCTT")
    ap.add_argument("--khoi-tao", action="store_true", help="tạo kho lần đầu từ vanhanhthuydien.xls")
    ap.add_argument("--xay-lai-tu-tho", action="store_true",
                    help="dựng lại kho từ xls + JSON gốc đã lưu (giữ bản cũ làm sao lưu)")
    ap.add_argument("--den", help="lấy đến giờ này (mặc định: hiện tại), dạng 'YYYY-MM-DD HH:MM'")
    a = ap.parse_args()
    KHO.mkdir(parents=True, exist_ok=True)
    with open(F_KHOA, "w") as khoa:
        try:
            fcntl.flock(khoa, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("LỖI: một lần chạy khác đang cập nhật kho", file=sys.stderr)
            return 1
        try:
            if a.khoi_tao:
                khoi_tao()
            elif a.xay_lai_tu_tho:
                xay_lai_tu_tho()
            else:
                cap_nhat(a.den)
            return 0
        except LoiNguon as e:
            print(f"LỖI NGUỒN DỮ LIỆU: {e}\nKho KHÔNG bị thay đổi.", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
