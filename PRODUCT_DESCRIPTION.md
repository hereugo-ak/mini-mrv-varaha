# Mini-MRV: Science Writeup

## 1. Overview

Mini-MRV is a prototype of Varaha's soil carbon MRV pipeline for Indo-Gangetic wheat systems. It fetches real SoilGrids SOC data, runs a simplified RothC carbon balance model across three management scenarios, quantifies uncertainty via Monte Carlo (VMD0053), and produces a Verra-aligned PDF report.

**Study area:** Ludhiana (Punjab) and Karnal (Haryana) intensive rice-wheat belt with residue burning as the baseline problem.

## 2. Carbon Balance Equation

The model is a monthly time-stepper running 20 years per pixel:

```
SOC(t+1) = SOC(t) + C_input * h - k * SOC(t) * f_temp * f_moist * f_till
```

| Term | Meaning | Source |
|------|---------|--------|
| `C_input` | Annual carbon input from residues/roots (tC/ha) | NDVI proxy: `(ndvi - 0.30) * 5.5` |
| `h` | Humification coefficient (fraction of input that becomes stable SOC) | Literature: 0.12 burn, 0.20 retain, 0.32 FYM |
| `k` | Base decomposition rate (yr^-1), texture dependent | 0.032 Ludhiana loam, 0.028 Karnal sodic |
| `f_temp` | Monthly temperature modifier (0.7–1.6) | Regional climatology |
| `f_moist` | Monthly moisture modifier (0.45–1.30) | Regional climatology |
| `f_till` | Tillage modifier | 1.35 conventional, 0.92 zero-till |

C input is distributed evenly over Apr–Jun (post-harvest months 3–5). A floor of 5 tC/ha prevents unrealistic negative SOC.

## 3. Scenarios (Verra VM0042 style)

| Scenario | Practice | C input | h | f_till |
|----------|----------|---------|---|--------|
| CT_burn (baseline) | Conventional tillage + residue burning | retain * 0.48 | 0.12 | 1.35 |
| ZT_retain | Zero-till + residue retention | (ndvi-0.30)*5.5 | 0.20 | 0.92 |
| ZT_FYM | Zero-till + residue + FYM | retain + 0.85 | 0.32 | 0.92 |

**Credit = incremental_tco2e_vs_baseline** = project tCO2e minus CT_burn tCO2e per pixel. Positive = sequestration benefit.

## 4. Data Sources

| Input | Source | Status |
|-------|--------|--------|
| SOC 0-30cm | SoilGrids 250m (ISRIC WebDAV /vsicurl) | Real |
| NDVI | Mock proxy `clip(0.52 + 0.08*randn, 0.3, 0.75)` | Mock (real: Planetary Computer STAC) |
| Climate modifiers | Regional climatology monthly factors | Mock (real: ERA5 CDS API) |

## 5. Uncertainty (VMD0053)

Monte Carlo with 1000 runs per district-scenario. Priors:
- `k ~ Normal(k_base, 0.006)` clipped [0.015, 0.055]
- `C_input ~ Normal(mean, mean*0.15)` clipped [0.2, 6.0]
- `h ~ Normal(h, h*0.10)` clipped [0.06, 0.45]
- `f_till jitter ~ Normal(1.0, 0.06)`

**Deduction rule:** if 90% CI width > 50% of |mean|, use 5th percentile as conservative credit.

## 6. Verra VM0042 Mapping

| VM0042 Requirement | Prototype Implementation |
|--------------------|--------------------------|
| Project boundary | 2 districts, 250m SoilGrids pixels |
| Baseline vs project | CT_burn vs ZT_retain / ZT_FYM |
| Quantification | incremental delta SOC * 44/12 |
| Uncertainty (VMD0053) | Monte Carlo 1000, p5 conservative if width > 50% mean |
| Leakage | Not modeled (stated as limitation) |
| Additionality | Not formally tested (stated as limitation) |

## 7. Limitations

1. **No field SOC calibration**: absolute tCO2e is illustrative, incremental deltas are the valid signal
2. **RothC-lite, not DayCent**: no N2O/CH4, no soil horizons, no daily weather
3. **NDVI and climate are mock**: real implementation uses Planetary Computer STAC + ERA5 CDS
4. **No leakage or additionality testing**: would need paired plots or regional baselines

## 8. How to swap to DayCent

1. Replace `02_rothc_lite_model.py` with DayCent API wrapper
2. Feed daily ERA5 weather + SoilGrids soil horizons per pixel
3. Calibrate `k` and `h` using Bayesian MCMC (PyMC) against measured SOC from field plots
4. Add N2O and CH4 modules for full GHG balance
5. Parallelize with Dask, containerize, log runs with MLflow
