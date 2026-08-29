# test_rothc.py — basic sanity check on the SOC model
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import importlib.util

spec = importlib.util.spec_from_file_location("m2", pathlib.Path(__file__).resolve().parents[1] / "src" / "02_rothc_lite_model.py")
m2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m2)

import numpy as np
import pandas as pd


def test_soc_does_not_go_negative():
    # SOC should never drop below the 5.0 floor
    climate = pd.DataFrame({
        "f_temp": [1.0] * 12,
        "f_moist": [1.0] * 12,
    })
    traj = m2.run_soc_trajectory(soc0=30, c_input_annual=0.5, h=0.12, k=0.032,
                                 f_till=1.35, climate_df=climate, years=20)
    assert traj.min() >= 5.0, f"SOC went below floor: {traj.min()}"


def test_higher_c_input_means_more_soc():
    # more C input should lead to higher final SOC, all else equal
    climate = pd.DataFrame({"f_temp": [1.0] * 12, "f_moist": [1.0] * 12})
    low = m2.run_soc_trajectory(30, 0.5, 0.12, 0.032, 1.35, climate)
    high = m2.run_soc_trajectory(30, 3.0, 0.32, 0.032, 0.92, climate)
    assert high[-1] > low[-1], f"High input should beat low: {high[-1]} vs {low[-1]}"


def test_delta_is_bounded():
    # 20-year delta should be reasonable (not > 50 tC/ha)
    climate = pd.DataFrame({"f_temp": [1.0] * 12, "f_moist": [1.0] * 12})
    traj = m2.run_soc_trajectory(30, 2.0, 0.20, 0.032, 0.92, climate, years=20)
    delta = traj[-1] - traj[0]
    assert abs(delta) < 50, f"Delta too large: {delta}"
