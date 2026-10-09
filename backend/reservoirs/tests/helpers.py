"""Test fixtures: a small data store written to a temporary folder (same file formats as
kho_du_lieu/), loaded with the real commands, and the real du_bao/ models."""
import io
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from accounts.models import User
from accounts.tests.helpers import BaseAPITestCase

COLUMNS = ["av_mn", "av_den", "av_may", "av_tran", "dm_mn", "dm_den", "dm_may", "dm_tran",
           "sb_mn", "sb_den", "sb_may", "sb_tran", "q_vugia", "st_mn", "st_den", "st_may",
           "st_tran", "q_thubon"]
BASE_LEVEL = {"av": 375.0, "dm": 255.0, "sb": 219.0, "st": 170.0}
RAIN_FILES = {"a_vuong": "mua_a_vuong.csv", "dak_mi_4": "mua_dak_mi_4.csv",
              "song_bung_4": "mua_song_bung_4.csv", "song_tranh_2": "mua_song_tranh_2.csv"}
START = pd.Timestamp("2025-10-01 00:00")
HOURS = 400
END = START + pd.Timedelta(hours=HOURS - 1)          # 2025-10-17 15:00
RAMP_HOURS = 24                                      # A Vương rises 0.15 m/h at the end
REAL_STORE = Path(settings.PROJECT_DIR) / "kho_du_lieu"


def synthetic_frames():
    idx = pd.date_range(START, periods=HOURS, freq="h")
    t = np.arange(HOURS)
    data = {}
    for p, base in BASE_LEVEL.items():
        data[f"{p}_mn"] = base + 0.3 * np.sin(t / 24 * 2 * np.pi) + 0.002 * t
        data[f"{p}_den"] = 100 + 20 * np.sin(t / 12)
        data[f"{p}_may"] = np.full(HOURS, 80.0)
        data[f"{p}_tran"] = np.zeros(HOURS)
    data["av_mn"][-RAMP_HOURS:] += 0.15 * np.arange(1, RAMP_HOURS + 1)
    data["q_vugia"], data["q_thubon"] = np.full(HOURS, 300.0), np.full(HOURS, 400.0)
    ops = pd.DataFrame(data, index=idx)[COLUMNS].round(2)
    rain = pd.Series(np.round(np.clip(2 * np.sin(t / 7), 0, None), 2), index=idx)
    return ops, {key: rain for key in RAIN_FILES}


def write_store(folder, ops, rains):
    (folder / "van_hanh").mkdir(parents=True)
    (folder / "mua_data").mkdir()
    out = ops.reset_index().rename(columns={"index": "thoi_gian"})
    out["thoi_gian"] = out["thoi_gian"].dt.strftime("%Y-%m-%d %H:%M")
    out.to_csv(folder / "van_hanh" / "van_hanh.csv", index=False, encoding="utf-8-sig",
               lineterminator="\n", float_format="%.2f")
    for key, series in rains.items():
        pd.DataFrame({"thoi_gian": series.index.strftime("%Y-%m-%d %H:%M"),
                      "mua_mm": series.to_numpy()}).to_csv(
            folder / "mua_data" / RAIN_FILES[key], index=False, encoding="utf-8-sig")
    (folder / "ngoai_le_thu_cong.csv").write_text("ho,bat_dau,ket_thuc,ly_do\n", encoding="utf-8")


def real_frames(start, end):
    """A slice of the real data store (only when kho_du_lieu/ exists on this machine)."""
    ops = pd.read_csv(REAL_STORE / "van_hanh" / "van_hanh.csv", encoding="utf-8-sig",
                      parse_dates=["thoi_gian"]).set_index("thoi_gian").loc[start:end, COLUMNS]
    rains = {}
    for key, name in RAIN_FILES.items():
        m = pd.read_csv(REAL_STORE / "mua_data" / name, encoding="utf-8-sig",
                        usecols=["thoi_gian", "mua_mm"], parse_dates=["thoi_gian"])
        rains[key] = m.set_index("thoi_gian")["mua_mm"].loc[start:end]
    return ops, rains


def aware(ts):
    return timezone.make_aware(pd.Timestamp(ts).to_pydatetime())


class ReservoirTestCase(BaseAPITestCase):
    """Loads wards, the base data and a temporary data store with the real commands."""
    frames = staticmethod(synthetic_frames)

    def setUp(self):
        super().setUp()
        self.store = Path(tempfile.mkdtemp(prefix="kho_test_"))
        self.addCleanup(shutil.rmtree, self.store, ignore_errors=True)
        override = override_settings(DATA_STORE_DIR=self.store)
        override.enable()
        self.addCleanup(override.disable)
        self.ops, self.rains = self.frames()
        write_store(self.store, self.ops, self.rains)
        self.run_command("load_wards", verbosity=0)
        self.run_command("load_reservoirs")
        self.run_command("load_history")

    def run_command(self, name, *args, **kwargs):
        out = io.StringIO()
        call_command(name, *args, stdout=out, **kwargs)
        return out.getvalue()

    def at(self, ts, minutes=0):
        """Freeze 'now' at a naive local time (+ minutes)."""
        patcher = mock.patch("django.utils.timezone.now",
                             return_value=aware(ts) + timedelta(minutes=minutes))
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_staff(self):
        self.admin = self.make_user("admin@example.com", "0922222222", role=User.Role.ADMIN)
        self.rescue = self.make_user("doi@example.com", "0933333333", role=User.Role.RESCUE_TEAM)
        self.citizen = self.make_user()
