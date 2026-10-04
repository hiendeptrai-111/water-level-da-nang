"""Dự báo thời gian thực mực nước và cảnh báo dâng nhanh cho 4 hồ.

    from du_bao import du_bao
    kq = du_bao("a_vuong", du_lieu_gan_nhat)

du_lieu_gan_nhat: DataFrame theo giờ, ít nhất 170 giờ gần nhất, chỉ số là thời gian
(DatetimeIndex) hoặc có cột "thoi_gian", gồm các cột:
    mn   mực nước hồ (m)          den  lưu lượng đến (m3/s)
    may  lưu lượng qua máy (m3/s)  tran lưu lượng qua tràn (m3/s)
    mua  mưa giờ của lưu vực hồ (mm)
Dòng cuối cùng là giờ hiện tại. Không được đưa dữ liệu tương lai vào.

Lỗi cấu trúc đầu vào (sai tên hồ, thiếu cột, ít hơn 170 giờ) -> ValueError.
Vấn đề chất lượng dữ liệu (thiếu giờ, giá trị ngoài phạm vi, gai) -> ghi vào
canh_bao_du_lieu; nếu không đủ dữ liệu để tính thì các trường dự báo là None.

Khi mực nước mới nhất lệch > 0.8 m so với giờ trước (NGHI NGỜ): dùng số liệu vận hành
giờ trước để tính, trả can_xac_nhan = True kèm lý do, muc_canh_bao tối thiểu "theo_doi";
không bao giờ lên "canh_bao" chỉ từ giá trị nghi ngờ. Ngưỡng vận hành: models/nguong_van_hanh.json.

Quy trình làm sạch và đặc trưng dùng chung xu_ly_du_lieu.py với lúc huấn luyện.
"""
import hashlib
import json
import warnings
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost

import xu_ly_du_lieu as xl
from xu_ly_du_lieu import COT_HO, HO, NGUONG, TAM, loc_gai, noi_suy_toi_da, tao_dac_trung

GOC = Path(__file__).resolve().parent
MD = GOC / "models"
F_NGUONG_VAN_HANH = MD / "nguong_van_hanh.json"
MUC = ["binh_thuong", "theo_doi", "canh_bao"]
TAM_CO_MUC_NUOC = (1, 3)  # chỉ trả mực nước dự kiến và A_bao cho các tầm này
GAI_THOI_GIAN_THUC = xl.GAI_LECH  # lệch so với giờ trước -> nghi ngờ

_CACHE = {}


# ---------------------------------------------------------------- nạp mô hình
def _nap():
    if _CACHE:
        return _CACHE
    md = json.loads((MD / "metadata.json").read_text(encoding="utf-8"))
    for ten_tv, ban in [("scikit-learn", sklearn.__version__), ("xgboost", xgboost.__version__)]:
        if ban != md["phien_ban"][ten_tv]:
            warnings.warn(f"{ten_tv} {ban} khác phiên bản lúc huấn luyện "
                          f"({md['phien_ban'][ten_tv]}); nên huấn luyện lại (xem retrain.md).")
    mo_hinh = {}
    for key in HO:
        for H in TAM:
            for loai in ("hoi_quy", "xgb"):
                tt = md["mo_hinh"][key][f"{H}h"][loai]
                f = MD / tt["file"]
                if hashlib.sha256(f.read_bytes()).hexdigest() != tt["sha256"]:
                    raise RuntimeError(f"{f.name} không khớp metadata.json — chạy lại train_final.py")
                mo_hinh[(key, H, loai)] = joblib.load(f)
    nguong = json.loads(F_NGUONG_VAN_HANH.read_text(encoding="utf-8")) \
        if F_NGUONG_VAN_HANH.exists() else {}
    if not nguong:
        warnings.warn(f"Không có {F_NGUONG_VAN_HANH} — so_voi_nguong_van_hanh sẽ rỗng")
    _CACHE.update(metadata=md, mo_hinh=mo_hinh, nguong=nguong)
    return _CACHE


def _chuan_hoa_ho(ho):
    if ho in HO:
        return ho
    for key, v in HO.items():
        if ho == v[0]:
            return key
    raise ValueError(f"Không biết hồ '{ho}'. Dùng một trong: {list(HO)}")


# ---------------------------------------------------------------- ngưỡng vận hành
def _trong_khoang(md, tu, den):
    return (tu <= md <= den) if tu <= den else (md >= tu or md <= den)  # cho phép vắt qua năm


def _gia_tri_nguong(cau_hinh, ngay):
    """Cấu hình một ngưỡng: số | None | {'gia_tri', 'tu', 'den', 'ap_dung'} | danh sách các dict.
    Trả về (giá trị hoặc None, mô tả khoảng áp dụng, khoảng đã xác nhận hay chưa)."""
    if cau_hinh is None:
        return None, "chưa cấu hình", False
    if isinstance(cau_hinh, (int, float)):
        return float(cau_hinh), "cả năm", True
    md = f"{ngay:%m-%d}"
    chua_xac_nhan = None
    for ky in (cau_hinh if isinstance(cau_hinh, list) else [cau_hinh]):
        if ky.get("tu") is None or ky.get("den") is None:
            chua_xac_nhan = chua_xac_nhan or ky   # chưa có mốc ngày: vẫn so sánh, ghi rõ
        elif _trong_khoang(md, ky["tu"], ky["den"]):
            return float(ky["gia_tri"]), f"{ky['tu']} → {ky['den']}", True
    if chua_xac_nhan is not None:
        return (float(chua_xac_nhan["gia_tri"]),
                f"chưa xác nhận ({chua_xac_nhan.get('ap_dung', '')})", False)
    return None, "ngoài các thời kỳ áp dụng", True


def _so_voi_nguong(muc_nuoc, key, ngay):
    if muc_nuoc is None:
        return None
    kq = {}
    for ten, cau_hinh in _nap()["nguong"].get(key, {}).items():
        g, khoang, xac_nhan = _gia_tri_nguong(cau_hinh, ngay)
        kq[ten] = {"nguong_m": g, "khoang_ap_dung": khoang,
                   "khoang_ap_dung_da_xac_nhan": xac_nhan}
        if g is not None:
            kq[ten].update(chenh_lech_m=round(muc_nuoc - g, 2) + 0.0, vuot=bool(muc_nuoc > g))
    return kq


# ---------------------------------------------------------------- chuẩn bị dữ liệu
def _chuan_bi(du_lieu, key):
    """Đưa về lưới giờ liên tục rồi làm sạch giống lúc huấn luyện, cộng bộ lọc gai
    thời gian thực cho giá trị mới nhất. Trả về (bảng sạch, mực nước đo được, cảnh báo)."""
    cb = []
    d = du_lieu.copy()
    if "thoi_gian" in d.columns:
        d = d.set_index("thoi_gian")
    thieu_cot = [c for c in COT_HO if c not in d.columns]
    if thieu_cot:
        raise ValueError(f"Thiếu cột {thieu_cot}; cần đủ {COT_HO}")
    d.index = pd.to_datetime(d.index).round("h")
    d = d[~d.index.duplicated(keep="last")].sort_index()[COT_HO].astype(float)
    luoi = pd.date_range(d.index.min(), d.index.max(), freq="h")
    can = _nap()["metadata"]["so_gio_toi_thieu_dau_vao"]
    if len(luoi) < can:
        raise ValueError(f"Cần ít nhất {can} giờ dữ liệu liên tục gần nhất, mới có {len(luoi)} giờ")
    d = d.reindex(luoi)
    so_gio_thieu = int(d["mn"].isna().sum())
    if so_gio_thieu:
        cb.append(f"Thiếu {so_gio_thieu} giờ mực nước trong {len(d)} giờ đầu vào "
                  f"(nội suy nếu khoảng trống <= {xl.NOI_SUY_TOI_DA} giờ)")

    lo, hi = HO[key][3]
    ngoai = d["mn"].notna() & ~d["mn"].between(lo, hi)
    if ngoai.any():
        cb.append(f"{int(ngoai.sum())} giá trị mực nước ngoài phạm vi [{lo}, {hi}] m bị loại "
                  f"(gần nhất {ngoai[ngoai].index[-1]:%d/%m %H:%M})")
        d.loc[ngoai, "mn"] = np.nan
    for c in ("den", "may", "tran"):
        sai = (d[c] < 0) | (d[c] > xl.LUU_LUONG_MAX)
        if sai.any():
            cb.append(f"{int(sai.sum())} giá trị '{c}' âm hoặc > {xl.LUU_LUONG_MAX} bị loại")
            d.loc[sai, c] = np.nan

    mn_do_duoc = d["mn"].iloc[-1]

    # Bộ lọc gai như lúc huấn luyện, cho các giờ đã có giờ sau
    d["mn"], doan, _ = loc_gai(d["mn"])
    gan = [g for g in doan if g[0] >= d.index[-1] - pd.Timedelta(hours=max(xl.TRE))]
    if gan:
        cb.append("Đã loại gai mực nước trong 48 giờ gần nhất: " + "; ".join(
            f"{t0:%d/%m %H:%M} ({' / '.join(f'{u:.2f}' for u in v)} m, trước {a:.2f}, sau {b:.2f})"
            for t0, _, a, v, b in gan))

    d = d.apply(noi_suy_toi_da)

    # Bộ lọc gai thời gian thực cho giờ mới nhất (chưa có giờ sau). Hàm không giữ trạng
    # thái: giờ tiếp theo, giá trị này đã có "giờ sau" nên loc_gai ở trên sẽ tự quyết
    # định — quay về mức cũ thì bị loại là gai, giữ mức mới thì được chấp nhận là thật.
    # Mực nước và lưu lượng đến/máy/tràn cùng một bản ghi vận hành: khi mực nước nghi ngờ
    # thì cả bản ghi đáng ngờ (ví dụ thật 25/10/2025 08:00 A Vương: mực nước +1,21 m, đồng
    # thời lưu lượng đến 120 -> 250, qua máy và tràn về 0) -> giữ cả 4 cột ở giờ trước.
    # Mưa đến từ nguồn khác nên giữ nguyên.
    mn_t, mn_truoc = d["mn"].iloc[-1], d["mn"].iloc[-2]
    ly_do_nghi_ngo = None
    if pd.notna(mn_t) and pd.notna(mn_truoc) and abs(mn_t - mn_truoc) > GAI_THOI_GIAN_THUC:
        cot_vh = ["mn", "den", "may", "tran"]
        ly_do_nghi_ngo = (f"Mực nước mới nhất {mn_t:.2f} m lệch {mn_t - mn_truoc:+.2f} m so với giờ "
                          f"trước ({mn_truoc:.2f} m), vượt ngưỡng {GAI_THOI_GIAN_THUC} m/giờ — có thể là "
                          "lỗi số liệu hoặc nước dâng/rút thật rất nhanh; cần kiểm tra trực tiếp")
        cb.append(f"NGHI NGỜ: {ly_do_nghi_ngo}. Tạm dùng số liệu vận hành (mực nước, lưu lượng) "
                  "của giờ trước để tính; giờ sau sẽ xác nhận")
        d.iloc[-1, [d.columns.get_loc(c) for c in cot_vh]] = d[cot_vh].iloc[-2].values
    elif pd.notna(mn_t) and pd.isna(mn_truoc):
        cb.append("Không kiểm tra được gai cho giá trị mới nhất vì thiếu mực nước giờ trước")
    return d, mn_do_duoc, cb, ly_do_nghi_ngo


# ---------------------------------------------------------------- hàm chính
def _muc_khi_nghi_ngo(muc, can_xac_nhan):
    """Khi giá trị mới nhất bị nghi ngờ: mức tối thiểu là "theo_doi" để người trực kiểm tra.
    Không bao giờ lên "canh_bao" chỉ vì giá trị nghi ngờ — giá trị đó đã được thay bằng số
    liệu giờ trước, nên "canh_bao" (nếu có) chỉ có thể đến từ diễn biến trước đó."""
    if not can_xac_nhan:
        return muc
    return max(muc or "binh_thuong", "theo_doi", key=MUC.index)


def du_bao(ho, du_lieu_gan_nhat):
    key = _chuan_hoa_ho(ho)
    tai_nguyen = _nap()
    md = tai_nguyen["metadata"]
    d, mn_do_duoc, cb_chung, ly_do_nghi_ngo = _chuan_bi(du_lieu_gan_nhat, key)
    can_xac_nhan = ly_do_nghi_ngo is not None
    t = d.index[-1]

    X = tao_dac_trung(d)[md["dac_trung"]]
    x = X.iloc[[-1]]
    thieu = [c for c in x.columns if pd.isna(x[c].iloc[0])]
    if thieu:
        goc = sorted({c.split("_")[0] for c in thieu})
        cb_chung.append(f"Không đủ dữ liệu để dự báo: thiếu {len(thieu)} đặc trưng "
                        f"(liên quan cột {goc}), ví dụ {thieu[:5]}")
    mn_dung = None if thieu else float(x["mn"].iloc[0])

    kq = {"ho": key, "ten_ho": HO[key][0], "thoi_diem": f"{t:%Y-%m-%d %H:%M}",
          "muc_nuoc_do_duoc": None if pd.isna(mn_do_duoc) else float(mn_do_duoc),
          "muc_nuoc_dung_de_tinh": mn_dung,
          "can_xac_nhan": can_xac_nhan, "ly_do_can_xac_nhan": ly_do_nghi_ngo,
          "so_voi_nguong_van_hanh_hien_tai": _so_voi_nguong(mn_dung, key, t.date())}

    for H in TAM:
        cb = list(cb_chung)
        r = {"muc_nuoc_du_kien": None, "thay_doi_du_kien_m": None, "baseline_bao": None,
             "A_bao": None, "B_bao": None, "xac_suat_xgb": None, "muc_canh_bao": None,
             "muc_canh_bao_tu_mo_hinh": None, "can_xac_nhan": can_xac_nhan,
             "ly_do_can_xac_nhan": ly_do_nghi_ngo,
             "so_voi_nguong_van_hanh": None, "canh_bao_du_lieu": cb}
        kq[f"{H}h"] = r
        if thieu:
            r["muc_canh_bao"] = _muc_khi_nghi_ngo(None, can_xac_nhan)
            continue
        tt = md["mo_hinh"][key][f"{H}h"]
        dy = float(tai_nguyen["mo_hinh"][(key, H, "hoi_quy")].predict(x)[0])
        baseline = bool(x[f"dang_mn{H}"].iloc[0] > NGUONG)
        p_xgb = float(tai_nguyen["mo_hinh"][(key, H, "xgb")].predict_proba(x)[0, 1])
        if tt["xgb"]["da_danh_gia"]:
            b = baseline or p_xgb >= md["muc_tieu"]["nguong_xac_suat_xgb"]
        else:
            b = baseline
            cb.append(f"XGBoost tầm {H}h của hồ này chưa được đánh giá (không đủ ca dâng nhanh) "
                      "— B_bao chỉ dựa vào Baseline")
        r.update(baseline_bao=baseline, B_bao=bool(b), xac_suat_xgb=round(p_xgb, 4))
        a = None
        if H in TAM_CO_MUC_NUOC:
            a = bool(dy > NGUONG)
            r.update(muc_nuoc_du_kien=round(mn_dung + dy, 2), thay_doi_du_kien_m=round(dy, 3),
                     A_bao=a,
                     so_voi_nguong_van_hanh=_so_voi_nguong(mn_dung + dy, key,
                                                           (t + pd.Timedelta(hours=H)).date()))
        muc = "canh_bao" if baseline or a else "theo_doi" if b else "binh_thuong"
        r["muc_canh_bao_tu_mo_hinh"] = muc
        r["muc_canh_bao"] = _muc_khi_nghi_ngo(muc, can_xac_nhan)

    muc_cac_tam = [kq[f"{H}h"]["muc_canh_bao"] for H in TAM if kq[f"{H}h"]["muc_canh_bao"]]
    kq["muc_canh_bao_chung"] = max(muc_cac_tam, key=MUC.index) if muc_cac_tam else None
    return kq


if __name__ == "__main__":  # ví dụ: dự báo tại giờ cuối cùng của dữ liệu lịch sử
    import pprint
    tho = xl.doc_du_lieu_tho(in_ra=lambda *a: None)
    for key, (ten, p, f_mua, _) in HO.items():
        bang = pd.DataFrame({k: tho[f"{p}_{k}"] for k in COT_HO[:4]})
        bang["mua"] = xl.doc_mua(f_mua).reindex(bang.index)
        bang = bang.loc[:"2025-10-28 12:00"].iloc[-200:]
        print(f"\n===== {ten} =====")
        pprint.pprint(du_bao(key, bang), sort_dicts=False, width=110)
