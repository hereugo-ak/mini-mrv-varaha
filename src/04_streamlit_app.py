# 04_streamlit_app.py: dashboard for Mini-MRV
# Shows scenario bars, Monte Carlo histograms, Verra alignment, CSV download.
# Run: streamlit run src/04_streamlit_app.py
import pathlib
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"

st.set_page_config(page_title="Mini-MRV", layout="wide", initial_sidebar_state="expanded")

st.title("Mini-MRV: Soil Carbon: Indo-Gangetic Wheat Systems")
st.caption("RothC-lite (not DayCent)  •  Verra VM0042 / VMD0053  •  Ludhiana + Karnal")


@st.cache_data
def load_data():
    results = pd.read_csv(PROC / "results.csv") if (PROC / "results.csv").exists() else None
    unc = pd.read_csv(PROC / "uncertainty_summary.csv") if (PROC / "uncertainty_summary.csv").exists() else None
    draws = pd.read_csv(PROC / "uncertainty_draws.csv") if (PROC / "uncertainty_draws.csv").exists() else None
    return results, unc, draws


results, unc, draws = load_data()

if results is None or unc is None:
    st.warning("Run 01-03 first: `python src/01_fetch_inputs.py && python src/02_rothc_lite_model.py && python src/03_uncertainty.py`")
    st.stop()

# sidebar
st.sidebar.header("Scenario")
scenario = st.sidebar.radio("Practice:", ["ZT_retain", "ZT_FYM", "CT_burn"], index=0)
district = st.sidebar.selectbox("District", ["Ludhiana", "Karnal", "Both"], index=2)
st.sidebar.info("**Read:** incremental_tco2e = project minus baseline (CT_burn). Positive = credit.")

# KPIs from incremental
inc = results[results["scenario"] == scenario]
if district != "Both":
    inc = inc[inc["district"] == district]
kpi = inc.groupby("district")["incremental_tco2e_vs_baseline"].mean().round(2)

cols = st.columns(3)
for i, (d, v) in enumerate(kpi.items()):
    with cols[i % 3]:
        st.metric(label=f"{d}: {scenario}", value=f"{v} tCO2e/ha/yr", delta="vs CT_burn baseline")

tab1, tab2, tab3 = st.tabs(["📊 Results", "🔬 Uncertainty", "📄 Verra"])

with tab1:
    st.subheader("Incremental tCO2e vs baseline (CT_burn)")
    chart_df = results[results["scenario"] == scenario] if district == "Both" else results[(results["scenario"] == scenario) & (results["district"] == district)]
    means = chart_df.groupby("district")["incremental_tco2e_vs_baseline"].mean()
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(means.index, means.values, color=["#1f4e79", "#2e75b6"][:len(means)])
    ax.set_ylabel("incremental tCO2e / ha / yr")
    ax.set_title(f"{scenario} vs CT_burn")
    ax.axhline(0, color="gray", linewidth=0.8)
    st.pyplot(fig, use_container_width=True)
    st.dataframe(chart_df[["district", "scenario", "tco2e_per_ha_per_year", "incremental_tco2e_vs_baseline"]].head(20),
                 use_container_width=True, hide_index=True)
    st.download_button("Download results.csv", data=results.to_csv(index=False), file_name="mini_mrv_results.csv", mime="text/csv")

with tab2:
    st.subheader("Monte Carlo draws (200 per district-scenario)")
    if draws is not None:
        sel = draws[draws["scenario"] == scenario]
        if district != "Both":
            sel = sel[sel["district"] == district]
        fig2, ax2 = plt.subplots(figsize=(7, 3))
        for d in sel["district"].unique():
            ax2.hist(sel[sel["district"] == d]["tco2e_draw"], bins=20, alpha=0.5, label=d)
        ax2.set_xlabel("tCO2e / ha / yr"); ax2.set_ylabel("count")
        ax2.legend(); ax2.set_title(f"Uncertainty: {scenario}")
        st.pyplot(fig2, use_container_width=True)
        st.caption("VMD0053: if 90% CI width > 50% of |mean|, use 5th percentile as conservative credit.")
    st.dataframe(unc[unc["scenario"] == scenario], use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Verra VM0042 / VMD0053 alignment")
    st.table(pd.DataFrame([
        {"Requirement": "Project boundary", "Prototype": "2 districts, 250m pixels", "Evidence": "districts.gpkg + soc_soilgrids.csv"},
        {"Requirement": "Baseline vs project", "Prototype": "CT_burn vs ZT_retain / ZT_FYM", "Evidence": "results.csv"},
        {"Requirement": "Quantification", "Prototype": "incremental delta SOC * 44/12", "Evidence": "incremental_tco2e_vs_baseline"},
        {"Requirement": "Uncertainty (VMD0053)", "Prototype": "Monte Carlo 1000, p5 conservative if width > 50% mean", "Evidence": "uncertainty_summary.csv"},
    ]))
    st.info("NDVI is a mock proxy (real: Planetary Computer STAC). Climate modifiers are mock (real: ERA5 CDS). No field SOC calibration.")

st.divider()
st.caption("MD Abuzar Salim - B.Sc Agriculture + MBA IB, AMU  |  github.com/hereugo-ak")
