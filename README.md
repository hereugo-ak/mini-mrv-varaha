# Mini-MRV: Soil Carbon Sequestration Estimator - Indo-Gangetic Wheat System

## 1. Run in 3 commands

```bash
git clone https://github.com/hereugo-ak/mini-mrv-varaha.git
cd mini-mrv-varaha
pip install -r requirements.txt

# fetch SoilGrids SOC (real, needs network) + NDVI proxy for Ludhiana + Karnal
python src/01_fetch_inputs.py

# run model + uncertainty
python src/02_rothc_lite_model.py
python src/03_uncertainty.py

# launch dashboard
streamlit run src/04_streamlit_app.py
```

Outputs: `data/processed/results.csv`, `data/processed/uncertainty_summary.csv`, `reports/Mini_MRV_Report_VM0042.pdf`

Sample outputs are committed in `data/` and `reports/` so you can review without running.

### Sample results (first 5 rows)

| district | scenario | soc0 | soc_final_20y | tco2e/ha/yr | incremental vs CT_burn |
|----------|----------|------|---------------|-------------|------------------------|
| Ludhiana | CT_burn | 29.0 | 15.4 | -2.49 | 0.00 |
| Ludhiana | ZT_retain | 29.0 | 23.6 | -0.99 | +1.51 |
| Ludhiana | ZT_FYM | 29.0 | 31.5 | +0.46 | +2.96 |
| Ludhiana | CT_burn | 30.0 | 15.1 | -2.73 | 0.00 |
| Ludhiana | ZT_retain | 30.0 | 21.3 | -1.60 | +1.13 |

`incremental_tco2e_vs_baseline` is the credit signal: positive means the project practice sequesters more carbon than the CT_burn baseline.

## 2. What it does

**Study area:** Ludhiana (Punjab) and Karnal (Haryana), Indo-Gangetic rice-wheat belt you know from field work.

**Scenarios (Verra VM0042 style):**

- **Baseline:** Conventional tillage + residue burning (CT_burn), low C input, high decomposition
- **Project 1:** Zero-till + residue retention (ZT_retain)
- **Project 2:** Zero-till + residue + Farm Yard Manure (ZT_FYM)

Delta SOC between project and baseline → tCO2e = delta SOC * 3.67, reported as tCO2e per ha per year with 95% CI from Monte Carlo 1000 runs.

## 3. Architecture

```
SoilGrids 250m SOC 0-30cm (ISRIC WebDAV) ─┐
NDVI proxy (mock, real: Planetary Computer)─┼─> 01_fetch_inputs.py ─> data/raw/
Climate modifiers (mock, real: ERA5 CDS) ──┘

                     ─> 02_rothc_lite_model.py (RothC-lite, not DayCent)
                     ─> 03_uncertainty.py (Monte Carlo, prior on k)
                     ─> 04_streamlit_app.py (charts + histograms)
                     ─> 05_report.py (MVR PDF)
```

Core equation (RothC simplified):
`SOC(t+1) = SOC(t) + C_input*h - k*SOC(t)*f_temp*f_moisture*f_tillage`

See `PRODUCT_DESCRIPTION.md` for full science writeup.



