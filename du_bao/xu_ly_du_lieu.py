"""Quy trình đọc dữ liệu, làm sạch, tạo đặc trưng và định nghĩa mô hình dùng CHUNG cho
đánh giá (train_4_mo_hinh.py), huấn luyện bản cuối (train_final.py) và dự báo thời gian
thực (du_bao.py). Sửa ở đây là sửa cho cả ba — sau khi sửa phải chạy lại đánh giá.
"""
import io
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

GOC = Path(__file__).resolve().parent

COT = ["ngay", "gio", "av_mn", "av_den", "av_may", "av_tran",
       "dm_mn", "dm_den", "dm_may", "dm_tran",
       "sb_mn", "sb_den", "sb_may", "sb_tran", "q_vugia",
       "st_mn", "st_den", "st_may", "st_tran", "q_thubon"]
HO = {  # khóa: (tên hiển thị, tiền tố cột, file mưa, giới hạn mực nước)
    "a_vuong": ("A Vương", "av", "mua_a_vuong.csv", (300, 381)),
    "dak_mi_4": ("Đăk Mi 4", "dm", "mua_dak_mi_4.csv", (200, 259)),
    "song_bung_4": ("Sông Bung 4", "sb", "mua_song_bung_4.csv", (180, 223.5)),
    "song_tranh_2": ("Sông Tranh 2", "st", "mua_song_tranh_2.csv", (130, 176)),
}
COT_HO = ["mn", "den", "may", "tran", "mua"]  # 5 cột của một hồ sau khi tách
TAM = [1, 3, 6]
TRE = [1, 2, 3, 6, 12, 24, 48]
TICH_LUY = [3, 6, 12, 24, 48, 72, 168]
NGUONG = 0.3
NGAY_BAT_DAU = "2024-06-01"
LUU_LUONG_MAX = 20000
NOI_SUY_TOI_DA = 6
# Lọc gai: "đoạn gai" là 1 hoặc 2 giờ liên tiếp mà mọi giá trị trong đoạn lệch
# > 0.8 m so với cả giá trị ngay trước và ngay sau đoạn, trong khi hai giá trị
# này chênh nhau < 0.5 m (nhảy lệch rồi quay về) -> lỗi nhập liệu. Chạy lặp.
GAI_LECH, GAI_VE = 0.8, 0.5
F_NGOAI_LE = GOC / "ngoai_le_thu_cong.csv"


def tim_file(ten, thu_muc=("data", ".", "mua_data")):
    """Tìm file trong data/ (theo đặc tả) hoặc các thư mục thực tế."""
    for t in thu_muc:
        p = GOC / t / ten
        if p.exists():
            return p
    raise FileNotFoundError(ten)


# ---------------------------------------------------------------- 1. đọc dữ liệu
def sang_so(s):
    """Chuyển chuỗi kiểu '1.234,5' thành số; giữ nguyên nếu pandas đã parse."""
    if s.dtype.kind in "fi":
        return s.astype(float)
    x = s.astype(str).str.strip()
    x = x.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(x, errors="coerce")


# ---------------------------------------------------------------- bỏ trùng mốc giờ
QT_KHONG_MAU_THUAN = "khong_mau_thuan"          # các bản ghi trùng giống hệt nhau
QT_GAN_TRUNG_BINH = "gan_trung_binh_lan_can"     # chọn theo trung bình giờ trước/sau
QT_SAU_CUNG = "sau_cung_khong_xac_dinh"          # giờ kề bên trùng/thiếu -> bản sau cùng
QT_SAU_CUNG_HOA = "sau_cung_hoa_khoang_cach"     # nhiều bản cách đều trung bình -> sau cùng


def bo_trung_moc_gio(bang):
    """Bỏ trùng mốc giờ, dùng chung cho huấn luyện và kho dữ liệu.

    bang: cột thoi_gian (đã làm tròn giờ) + COT[2:], thứ tự dòng = thứ tự xuất hiện trong nguồn.
    Với mỗi hồ, nếu một mốc giờ có nhiều bản ghi khác nhau ở 4 cột vận hành của hồ đó:
      - chọn bản ghi có mực nước gần nhất với trung bình mực nước giờ trước và giờ sau,
        lấy từ các giờ kề bên KHÔNG mâu thuẫn (một giá trị duy nhất) ở cột mực nước hồ đó;
      - không xác định được (giờ kề bên cũng mâu thuẫn hoặc thiếu) -> bản xuất hiện sau cùng;
      - nhiều bản cách đều trung bình -> bản sau cùng trong số đó.
    Lấy nguyên 4 cột (mn, den, may, tran) của hồ từ CÙNG một bản ghi; mỗi hồ chọn độc lập.
    q_vugia, q_thubon (không dùng trong mô hình): lấy từ bản xuất hiện sau cùng.
    Trả về (bảng chỉ số thoi_gian đã sắp xếp, nhật ký các (giờ, hồ) có mâu thuẫn)."""
    bang = bang.reset_index(drop=True)
    sau_cung = bang.groupby("thoi_gian", sort=True).tail(1).set_index("thoi_gian").sort_index()
    ket_qua = sau_cung[COT[2:]].copy()
    so_dong = bang.groupby("thoi_gian").size()
    gio_trung = so_dong.index[so_dong > 1]
    nhat_ky = []
    if len(gio_trung) == 0:
        return ket_qua, pd.DataFrame(nhat_ky)
    trung = bang[bang["thoi_gian"].isin(gio_trung)]
    mot_gio = pd.Timedelta(hours=1)
    for key, (ten, p, _, _) in HO.items():
        cot4 = [f"{p}_{k}" for k in ("mn", "den", "may", "tran")]
        # giá trị mực nước "đáng tin" của từng giờ: đúng một giá trị (bỏ NaN) trên mọi bản ghi
        g = bang.groupby("thoi_gian")[f"{p}_mn"]
        mn_don = g.first().where(g.nunique() == 1)
        for t, nhom in trung.groupby("thoi_gian", sort=True):
            khac_nhau = nhom[cot4].round(6).astype(str).drop_duplicates()
            if len(khac_nhau) <= 1:
                continue                      # bản ghi trùng giống hệt ở hồ này
            tb = (mn_don.get(t - mot_gio, np.nan) + mn_don.get(t + mot_gio, np.nan)) / 2
            mn = nhom[f"{p}_mn"]
            if pd.isna(tb) or mn.notna().sum() == 0:
                chon, quy_tac = nhom.index[-1], QT_SAU_CUNG
            else:
                kc = (mn - tb).abs()
                tot = kc[np.isclose(kc, kc.min(), equal_nan=False)]
                chon = tot.index[-1]
                quy_tac = QT_GAN_TRUNG_BINH if len(tot) == 1 else QT_SAU_CUNG_HOA
            ket_qua.loc[t, cot4] = bang.loc[chon, cot4].values
            nhat_ky.append({"thoi_gian": t, "ho": key, "so_ban_ghi": len(nhom),
                            "gia_tri_mn": "; ".join("" if pd.isna(v) else f"{v:.2f}" for v in mn),
                            "tb_gio_ke_ben": None if pd.isna(tb) else round(float(tb), 3),
                            "mn_chon": bang.at[chon, f"{p}_mn"],
                            "mn_sau_cung": bang.at[nhom.index[-1], f"{p}_mn"],
                            "chon_ban_thu": int(list(nhom.index).index(chon)) + 1,
                            "quy_tac": quy_tac})
    return ket_qua, pd.DataFrame(nhat_ky)


def tom_tat_bo_trung(nhat_ky, so_gio_trung, in_ra=print):
    in_ra(f"  Bỏ trùng mốc giờ: {so_gio_trung:,} giờ có nhiều bản ghi; "
          f"{len(nhat_ky):,} cặp (giờ, hồ) có giá trị mâu thuẫn")
    if len(nhat_ky):
        for (ho, qt), n in nhat_ky.groupby(["ho", "quy_tac"]).size().items():
            in_ra(f"    {ho:<13} {qt:<26} {n:>5}")


def doc_du_lieu_tho(in_ra=print, tra_nhat_ky=False):
    """Đọc file vận hành, ghép ngày giờ, đổi sang số, bỏ trùng mốc giờ (bo_trung_moc_gio).
    Chưa lọc phạm vi, chưa lọc gai, chưa nội suy. tra_nhat_ky=True -> (bảng, nhật ký trùng)."""
    f_vh = tim_file("vanhanhthuydien.xls")
    with open(f_vh, encoding="utf-8") as f:
        html = f.read()
    df = pd.read_html(io.StringIO(html), header=None, decimal=",", thousands=".")[0]
    del html
    df = df.iloc[:, :20]
    df.columns = COT
    in_ra(f"  Đọc thô: {len(df):,} dòng")

    # Bỏ 3 dòng tiêu đề đầu (chỉ khi đúng là tiêu đề, tránh mất dữ liệu nếu pandas
    # đã tự tách phần thead thành header)
    dau = pd.to_datetime(df["ngay"].head(3).astype(str), format="%d/%m/%Y", errors="coerce")
    if dau.isna().all():
        df = df.iloc[3:]
        in_ra(f"  Bỏ 3 dòng tiêu đề: {len(df):,} dòng")
    else:
        in_ra("  3 dòng đầu đã là dữ liệu (pandas đã tách tiêu đề) -> không bỏ")

    df["thoi_gian"] = pd.to_datetime(df["ngay"].astype(str).str.strip() + " "
                                     + df["gio"].astype(str).str.strip(),
                                     format="%d/%m/%Y %H:%M", errors="coerce")
    df = df.dropna(subset=["thoi_gian"])
    in_ra(f"  Sau khi ghép ngày giờ (bỏ dòng lỗi): {len(df):,} dòng")
    df["thoi_gian"] = df["thoi_gian"].dt.round("h")
    for c in COT[2:]:
        df[c] = sang_so(df[c])
    so_gio_trung = int(df["thoi_gian"].duplicated().groupby(df["thoi_gian"]).any().sum())
    df, nhat_ky = bo_trung_moc_gio(df.drop(columns=["ngay", "gio"]))
    in_ra(f"  Sau khi bỏ trùng mốc giờ: {len(df):,} dòng "
          f"({df.index.min()} -> {df.index.max()})")
    tom_tat_bo_trung(nhat_ky, so_gio_trung, in_ra)
    return (df, nhat_ky) if tra_nhat_ky else df


F_KHO_VAN_HANH = GOC / "kho_du_lieu" / "van_hanh" / "van_hanh.csv"


def doc_kho_van_hanh(duong_dan=F_KHO_VAN_HANH, in_ra=print):
    """Đọc kho dữ liệu vận hành do cap_nhat_du_lieu_ho.py tạo. Trả về cùng dạng với
    doc_du_lieu_tho(): chỉ số thoi_gian theo giờ, 18 cột số, đã bỏ trùng mốc giờ."""
    df = pd.read_csv(duong_dan, encoding="utf-8-sig", parse_dates=["thoi_gian"])
    df = df.set_index("thoi_gian")[COT[2:]].astype(float).sort_index()
    if df.index.duplicated().any():
        raise RuntimeError(f"{duong_dan} có mốc giờ trùng — kho bị hỏng, kiểm tra lại")
    in_ra(f"  Kho vận hành: {len(df):,} dòng ({df.index.min()} -> {df.index.max()})")
    return df


def doc_mua(ten_file):
    m = pd.read_csv(tim_file(ten_file), encoding="utf-8-sig", usecols=["thoi_gian", "mua_mm"])
    m["thoi_gian"] = pd.to_datetime(m["thoi_gian"]).dt.round("h")
    return m.drop_duplicates("thoi_gian", keep="last").set_index("thoi_gian")["mua_mm"]


# ---------------------------------------------------------------- 2. làm sạch
def tim_doan_gai(x, dai):
    """Trả về mask các giờ BẮT ĐẦU một đoạn gai dài `dai` giờ."""
    truoc, sau = x.shift(1), x.shift(-dai)
    dk = (truoc - sau).abs() < GAI_VE
    for k in range(dai):
        v = x.shift(-k)
        dk &= ((v - truoc).abs() > GAI_LECH) & ((v - sau).abs() > GAI_LECH)
    return dk


def loc_gai(x):
    """Gán NaN cho các đoạn gai 1–2 giờ, lặp đến khi không còn gai mới.
    Trả về (chuỗi đã lọc, danh sách đoạn (bắt đầu, độ dài, trước, [giá trị], sau), số vòng)."""
    x = x.copy()
    doan = []
    vong = 0
    while True:
        vong += 1
        moi = []
        for dai in (1, 2):
            for t0 in x.index[tim_doan_gai(x, dai).values]:
                i = x.index.get_loc(t0)
                moi.append((t0, dai, x.iloc[i - 1], x.iloc[i:i + dai].tolist(), x.iloc[i + dai]))
        if not moi:
            break
        for t0, dai, _, _, _ in moi:
            i = x.index.get_loc(t0)
            x.iloc[i:i + dai] = np.nan
        doan += moi
    doan.sort(key=lambda d: d[0])
    return x, doan, vong - 1


def noi_suy_toi_da(s, gioi_han=NOI_SUY_TOI_DA):
    """Nội suy tuyến tính chỉ cho các khoảng trống dài <= gioi_han giờ."""
    thieu = s.isna()
    nhom = (~thieu).cumsum()
    do_dai = thieu.groupby(nhom).transform("sum")
    day = s.interpolate(method="linear", limit_area="inside")
    return day.where(~thieu | (do_dai <= gioi_han))


def nap_du_lieu_sach(ngay_tach=None, in_ra=print, f_nhat_ky_trung=None):
    """Toàn bộ quy trình làm sạch + ghép mưa. `ngay_tach` chỉ dùng để in số gai
    theo train/test (None = không tách). f_nhat_ky_trung: nơi lưu nhật ký bỏ trùng."""
    df, nhat_ky_trung = doc_du_lieu_tho(in_ra, tra_nhat_ky=True)
    if f_nhat_ky_trung is not None:
        nhat_ky_trung.to_csv(f_nhat_ky_trung, index=False, encoding="utf-8-sig")
        in_ra(f"  Nhật ký bỏ trùng: {f_nhat_ky_trung}")

    for key, (_, p, _, (lo, hi)) in HO.items():
        c = f"{p}_mn"
        ngoai = ~df[c].between(lo, hi) & df[c].notna()
        df.loc[ngoai, c] = np.nan
        in_ra(f"  {c}: gán NaN {ngoai.sum():,} giá trị ngoài [{lo}, {hi}]")
    so_sai = 0
    for c in [c for c in COT[2:] if not c.endswith("_mn")]:
        sai = (df[c] < 0) | (df[c] > LUU_LUONG_MAX)
        df.loc[sai, c] = np.nan
        so_sai += int(sai.sum())
    in_ra(f"  Lưu lượng âm hoặc > {LUU_LUONG_MAX}: gán NaN {so_sai:,} giá trị")

    df = df[df.index >= NGAY_BAT_DAU]
    in_ra(f"  Từ {NGAY_BAT_DAU}: {len(df):,} dòng")

    luoi = pd.date_range(df.index.min(), df.index.max(), freq="h")
    df = df.reindex(luoi)
    in_ra(f"  Lưới giờ liên tục: {len(df):,} dòng (thiếu {df['av_mn'].isna().sum():,} giờ mực nước A Vương)")

    # Loại trừ thủ công các đoạn lỗi đã kiểm tra bằng tay (đặt trước bước lọc gai để
    # các giá trị đúng nằm giữa đoạn lỗi không bị bộ lọc gai coi nhầm là gai)
    if F_NGOAI_LE.exists():
        ngoai_le = pd.read_csv(F_NGOAI_LE, encoding="utf-8-sig",
                               parse_dates=["bat_dau", "ket_thuc"])
        in_ra(f"  Loại trừ thủ công ({F_NGOAI_LE.name}):")
        for _, r in ngoai_le.iterrows():
            c = f"{HO[r['ho']][1]}_mn"
            doan = (df.index >= r["bat_dau"]) & (df.index <= r["ket_thuc"])
            df.loc[doan, c] = np.nan
            in_ra(f"    {HO[r['ho']][0]}: {r['bat_dau']:%d/%m/%Y %H:%M} → "
                  f"{r['ket_thuc']:%d/%m/%Y %H:%M} ({int(doan.sum())} giờ) – {r['ly_do']}")

    in_ra(f"  Lọc gai mực nước (đoạn 1–2 giờ, lệch > {GAI_LECH} m, quay về < {GAI_VE} m):")
    for key, (ten, p, _, _) in HO.items():
        x, doan, so_vong = loc_gai(df[f"{p}_mn"])
        df[f"{p}_mn"] = x
        if ngay_tach is not None:
            bang = pd.DataFrame([(d[0] < pd.Timestamp(ngay_tach), d[1]) for d in doan],
                                columns=["train", "dai"])
            dem = lambda tr, dai: int(((bang["train"] == tr) & (bang["dai"] == dai)).sum()) if len(bang) else 0
            in_ra(f"    {ten}: {len(doan)} đoạn gai ({so_vong} vòng lặp) | "
                  f"train: {dem(True, 1)} gai 1h + {dem(True, 2)} gai 2h | "
                  f"test: {dem(False, 1)} gai 1h + {dem(False, 2)} gai 2h")
        else:
            n2 = sum(d[1] == 2 for d in doan)
            in_ra(f"    {ten}: {len(doan)} đoạn gai ({so_vong} vòng lặp) | "
                  f"{len(doan) - n2} gai 1h + {n2} gai 2h")
        for t0, dai, a, v, b in doan[:5]:
            in_ra(f"      {t0:%d/%m/%Y %H:%M} ({dai}h): {a:.2f} – "
                  f"{' / '.join(f'{u:.2f}' for u in v)} – {b:.2f}")

    truoc = int(df.isna().sum().sum())
    df = df.apply(noi_suy_toi_da)
    in_ra(f"  Nội suy (<= 6 giờ): lấp {truoc - int(df.isna().sum().sum()):,} ô, "
          f"còn thiếu {int(df.isna().sum().sum()):,} ô")

    in_ra("  Bước nhảy mực nước > 1 m trong 1 giờ còn sót lại (sau lọc gai + nội suy):")
    for key, (ten, p, _, _) in HO.items():
        x = df[f"{p}_mn"]
        nhay = x.diff().abs() > 1.0
        if ngay_tach is not None:
            n_tr = int((nhay & (df.index < ngay_tach)).sum())
            in_ra(f"    {ten}: {int(nhay.sum())} lần (train {n_tr}, test {int(nhay.sum()) - n_tr})")
        else:
            in_ra(f"    {ten}: {int(nhay.sum())} lần")
        for t in nhay[nhay].index[:5]:
            i = x.index.get_loc(t)
            w = " – ".join(f"{u:.2f}" for u in x.iloc[max(i - 2, 0):i + 3])
            in_ra(f"      {t:%d/%m/%Y %H:%M}: {w}   (từ t−2 đến t+2)")

    for key, (_, p, f_mua, _) in HO.items():
        df[f"{p}_mua"] = doc_mua(f_mua).reindex(df.index)
        in_ra(f"  Ghép mưa {f_mua}: {df[f'{p}_mua'].notna().sum():,}/{len(df):,} giờ có mưa")
    in_ra(f"  Bảng sau khi ghép mưa: {len(df):,} dòng x {df.shape[1]} cột")
    return df


def bang_ho(df, p):
    """Tách 5 cột của một hồ (tiền tố p) thành bảng cột mn, den, may, tran, mua."""
    return pd.DataFrame({k: df[f"{p}_{k}"] for k in COT_HO})


# ---------------------------------------------------------------- 3. đặc trưng
def tao_dac_trung(d):
    """d: bảng theo giờ liên tục, cột mn, den, may, tran, mua."""
    X = d[COT_HO].copy()
    for k in ["mn", "mua", "den", "tran"]:
        for l in TRE:
            X[f"{k}_tre{l}"] = d[k].shift(l)
    for w in TICH_LUY:
        X[f"mua_tl{w}"] = d["mua"].rolling(w, min_periods=w).sum()
    X["dang_mn1"] = d["mn"] - d["mn"].shift(1)
    X["dang_mn3"] = d["mn"] - d["mn"].shift(3)
    X["dang_mn6"] = d["mn"] - d["mn"].shift(6)
    X["dang_den3"] = d["den"] - d["den"].shift(3)
    X["dang_tran3"] = d["tran"] - d["tran"].shift(3)
    X["gio"] = X.index.hour
    X["thang"] = X.index.month
    return X


# ---------------------------------------------------------------- mô hình dùng cho hệ thống
def hoi_quy_tuyen_tinh():
    """Phương án A: hồi quy tuyến tính dự báo mức thay đổi mn(t+H) - mn(t)."""
    return make_pipeline(StandardScaler(), LinearRegression())


def xgb_phan_loai(spw):
    """Phương án B (cùng Baseline): XGBoost phân loại dâng > 0.3 m."""
    return XGBClassifier(n_estimators=500, max_depth=5, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
                         scale_pos_weight=spw, random_state=42)
