# 02_rothc_lite_model.py: RothC-lite proxy, NOT DayCent.
# Real DayCent needs soil horizons + daily weather + calibration with field SOC.
# SOC(t+1) = SOC(t) + C_input*h - k*SOC(t)*f_temp*f_moist*f_till
# Runs monthly for 20 years per pixel, per scenario.
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"

# humification fraction and decomposition params: texture dependent, from literature
PARAMS = {
    "h_burn": 0.12,       # burned residue leaves little humus
    "h_retain": 0.20,     # wheat straw
    "h_fym": 0.32,        # FYM more recalcitrant
    "k_ludhiana": 0.032,  # loam, slightly faster turnover
    "k_karnal": 0.028,    # sodic patches, slower
    "f_till_burn": 1.35,  # conventional tillage intensifies oxidation
    "f_till_zt": 0.92,    # zero-till protects aggregates
}

SCENARIOS = ["CT_burn", "ZT_retain", "ZT_FYM"]


def run_soc_trajectory(soc0, c_input_annual, h, k, f_till, climate_df, years=20):
    # monthly loop: C input added Apr-Jun (post-harvest), decomposition every month
    soc = np.zeros(years + 1)
    soc[0] = soc0
    monthly_c = np.zeros(12)
    monthly_c[3:6] = c_input_annual * h / 3.0
    f_temp = climate_df["f_temp"].values
    f_moist = climate_df["f_moist"].values
    for y in range(years):
        s = soc[y]
        for m in range(12):
            s = s + monthly_c[m] - k / 12.0 * s * f_temp[m] * f_moist[m] * f_till
            if s < 5.0:
                s = 5.0
        soc[y + 1] = s
    return soc


def main():
    print("=== 02_rothc_lite_model: running scenarios ===")
    c_inputs = pd.read_csv(PROC / "c_inputs.csv")
    climate = pd.read_csv(RAW / "climate_modifiers.csv")
    rows = []
    for idx, row in c_inputs.iterrows():
        district = row["district"]
        soc0 = row["soc_0_30_tC_per_ha"]
        k = PARAMS["k_ludhiana"] if district == "Ludhiana" else PARAMS["k_karnal"]
        for scenario, c_in, h, f_till in [
            ("CT_burn", row["c_input_burn_tC_per_ha"], PARAMS["h_burn"], PARAMS["f_till_burn"]),
            ("ZT_retain", row["c_input_retain_tC_per_ha"], PARAMS["h_retain"], PARAMS["f_till_zt"]),
            ("ZT_FYM", row["c_input_fym_tC_per_ha"], PARAMS["h_fym"], PARAMS["f_till_zt"]),
        ]:
            traj = run_soc_trajectory(soc0, c_in, h, k, f_till, climate, years=20)
            delta_annual = (traj[-1] - soc0) / 20.0
            rows.append({
                "pixel_id": idx,
                "district": district,
                "soc0": soc0,
                "scenario": scenario,
                "c_input": c_in,
                "soc_final_20y": traj[-1],
                "delta_soc_20y": traj[-1] - soc0,
                "delta_soc_per_year": delta_annual,
                "tco2e_per_ha_per_year": delta_annual * 3.67,  # 44/12
            })
    df = pd.DataFrame(rows)

    # incremental tco2e vs baseline (CT_burn): this is the actual credit
    baseline = df[df["scenario"] == "CT_burn"][["pixel_id", "tco2e_per_ha_per_year"]].rename(
        columns={"tco2e_per_ha_per_year": "baseline_tco2e"}
    )
    df = df.merge(baseline, on="pixel_id")
    df["incremental_tco2e_vs_baseline"] = df["tco2e_per_ha_per_year"] - df["baseline_tco2e"]
    df = df.drop(columns=["baseline_tco2e"])

    out = PROC / "results.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows to {out}")
    summary = df.groupby(["district", "scenario"])[
        ["tco2e_per_ha_per_year", "incremental_tco2e_vs_baseline"]
    ].mean().round(3)
    print(summary.to_string())
    print("\nIncremental = project - baseline (CT_burn). Positive = carbon credit.")
    print("Next: python src/03_uncertainty.py")


if __name__ == "__main__":
    main()
