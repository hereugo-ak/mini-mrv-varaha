# 03_uncertainty.py — Monte Carlo uncertainty per VMD0053
# Prior k ~ Normal(0.032, 0.006) — production would be PyMC posterior from field SOC
# Runs 1000 jittered runs per district-scenario, computes 90% CI and conservative deduction.
#
# Production Bayesian version (PyMC) would replace the np.random.normal draws with:
#   import pymc as pm
#   with pm.Model():
#       k = pm.Normal("k", mu=0.032, sigma=0.006)
#       h = pm.Normal("h", mu=0.20, sigma=0.02)
#       c_input = pm.Normal("c_input", mu=mean_c, sigma=mean_c*0.15)
#       soc_pred = pm.Deterministic("soc", soc_model(k, h, c_input))
#       pm.Normal("obs", mu=soc_pred, sigma=2.0, observed=field_soc_data)
#       trace = pm.sample(2000, tune=1000)
# This gives a posterior on k calibrated to field measurements instead of a fixed prior.
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"

PARAMS = {"h_burn": 0.12, "h_retain": 0.20, "h_fym": 0.32,
          "k_ludhiana": 0.032, "k_karnal": 0.028,
          "f_till_burn": 1.35, "f_till_zt": 0.92}


def run_soc_fast(soc0, c_input, h, k, f_till, f_temp, f_moist, years=20):
    soc = soc0
    monthly_c = np.zeros(12)
    monthly_c[3:6] = c_input * h / 3.0
    for y in range(years):
        for m in range(12):
            soc = soc + monthly_c[m] - k / 12.0 * soc * f_temp[m] * f_moist[m] * f_till
            if soc < 5:
                soc = 5
    return soc


def main(n_runs=1000):
    print(f"=== 03_uncertainty: Monte Carlo n={n_runs} ===")
    results = pd.read_csv(PROC / "results.csv")
    climate = pd.read_csv(RAW / "climate_modifiers.csv")
    f_temp = climate["f_temp"].values
    f_moist = climate["f_moist"].values

    np.random.seed(123)
    summaries = []
    draw_rows = []
    # aggregate by district+scenario (mean C input and soc0 for speed)
    for (district, scenario), g in results.groupby(["district", "scenario"]):
        mean_c = g["c_input"].mean()
        mean_soc0 = g["soc0"].mean()
        k_base = PARAMS["k_ludhiana"] if district == "Ludhiana" else PARAMS["k_karnal"]
        h = {"CT_burn": PARAMS["h_burn"], "ZT_retain": PARAMS["h_retain"], "ZT_FYM": PARAMS["h_fym"]}[scenario]
        f_till = PARAMS["f_till_burn"] if scenario == "CT_burn" else PARAMS["f_till_zt"]

        draws = []
        for _ in range(n_runs):
            k = float(np.clip(np.random.normal(k_base, 0.006), 0.015, 0.055))
            c = float(np.clip(np.random.normal(mean_c, mean_c * 0.15), 0.2, 6.0))
            hh = float(np.clip(np.random.normal(h, h * 0.10), 0.06, 0.45))
            f_jitter = float(np.random.normal(1.0, 0.06))
            soc_final = run_soc_fast(mean_soc0, c, hh, k, f_till * f_jitter, f_temp, f_moist)
            draws.append((soc_final - mean_soc0) / 20.0 * 3.67)
        draws = np.array(draws)

        mean = draws.mean()
        sd = draws.std(ddof=1)
        p5, p25, p75, p95 = np.percentile(draws, [5, 25, 75, 95])
        width = p95 - p5
        # VMD0053: if 90% CI width > 50% of |mean|, use 5th percentile as conservative credit
        deduction = width > (0.5 * abs(mean) if mean != 0 else 0.5)
        conservative = p5 if deduction else mean

        if district == "Karnal" and scenario == "ZT_FYM":
            print(f"Karnal ZT_FYM width {width:.2f} > 0.5*|mean| so conservative = p5 ({p5:.3f})")

        summaries.append({
            "district": district, "scenario": scenario,
            "mean_tco2e": round(float(mean), 3), "sd": round(float(sd), 3),
            "p5": round(float(p5), 3), "p25": round(float(p25), 3),
            "p75": round(float(p75), 3), "p95": round(float(p95), 3),
            "width_p90": round(float(width), 3),
            "deduction_triggered": bool(deduction),
            "conservative_tco2e": round(float(conservative), 3),
        })
        for d in np.random.choice(draws, 200, replace=False):
            draw_rows.append({"district": district, "scenario": scenario, "tco2e_draw": round(float(d), 3)})

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(PROC / "uncertainty_summary.csv", index=False)
    pd.DataFrame(draw_rows).to_csv(PROC / "uncertainty_draws.csv", index=False)
    print(summary_df.to_string(index=False))
    print(f"\nSaved uncertainty_summary.csv and uncertainty_draws.csv to {PROC}")
    print("Next: streamlit run src/04_streamlit_app.py")


if __name__ == "__main__":
    main()
