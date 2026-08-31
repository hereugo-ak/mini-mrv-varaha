# 05_report.py: 1-page MVR-style PDF (Verra VM0042 summary)
# Run: python src/05_report.py
import pathlib
from fpdf import FPDF
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)


def build_pdf():
    unc_path = PROC / "uncertainty_summary.csv"
    if not unc_path.exists():
        print("Run 01-03 first; no uncertainty_summary.csv found")
        return
    unc = pd.read_csv(unc_path)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=12)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 7, "Mini-MRV - Model Validation Report (MVR)", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(0, 4, "Indo-Gangetic Wheat (Ludhiana + Karnal)  |  RothC-lite (not DayCent)  |  Verra VM0042 / VMD0053", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)
    pdf.set_draw_color(31, 78, 121)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    # summary table
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 5, "Results - Mean and Conservative tCO2e per ha per year", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 6)
    cols = ["District", "Scenario", "Mean", "SD", "P5", "P95", "Width", "Deduct", "Conservative"]
    widths = [22, 22, 18, 16, 16, 16, 16, 18, 22]
    for i, c in enumerate(cols):
        pdf.cell(widths[i], 5, c, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 6)
    for _, r in unc.iterrows():
        vals = [r["district"], r["scenario"], f"{r['mean_tco2e']:.3f}", f"{r['sd']:.3f}",
                f"{r['p5']:.3f}", f"{r['p95']:.3f}", f"{r['width_p90']:.3f}",
                "YES" if r["deduction_triggered"] else "no", f"{r['conservative_tco2e']:.3f}"]
        for i, v in enumerate(vals):
            pdf.cell(widths[i], 4.5, str(v), border=1, align="C")
        pdf.ln()
    pdf.ln(2)

    # methodology
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 5, "Methodology", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 6.5)
    bullets = [
        "SOC: SoilGrids 250m OCS 0-30cm via ISRIC WebDAV (real). ~120 pixels per district, Ludhiana + Karnal.",
        "Model: RothC-lite SOC(t+1)=SOC(t)+C_input*h - k*SOC(t)*f_temp*f_moist*f_till; monthly, 20yr; h_burn 0.12, h_retain 0.20, h_FYM 0.32; k 0.032/0.028; f_till 1.35 CT vs 0.92 ZT.",
        "NDVI is a mock proxy (real: Planetary Computer STAC). C_retain=(NDVI-0.30)*5.5, C_burn=retain*0.48, C_FYM=retain+0.85.",
        "Credit = incremental_tco2e_vs_baseline (project minus CT_burn). Uncertainty: Monte Carlo 1000, k~N(base,0.006); VMD0053 deduction if 90% CI width > 50% of |mean|, conservative = p5.",
    ]
    for b in bullets:
        pdf.cell(4, 4, "-")
        pdf.multi_cell(0, 4, b.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(0.5)

    # limitations
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 5, "Limitations (honest)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 6.5)
    lims = [
        "No field SOC calibration; absolute tCO2e illustrative, incremental deltas are the valid signal.",
        "RothC-lite, NOT DayCent. No N2O/CH4. Real DayCent needs soil horizons + daily weather + field calibration.",
        "NDVI and climate modifiers are mock. Real: Planetary Computer STAC + ERA5 CDS.",
    ]
    for l in lims:
        pdf.cell(4, 4, "-")
        pdf.multi_cell(0, 4, l.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(0.5)

    # footer
    pdf.ln(1)
    pdf.set_font("Helvetica", "I", 6)
    pdf.multi_cell(0, 3.5, "MD Abuzar Salim - B.Sc Agriculture + MBA IB, AMU  |  github.com/hereugo-ak".encode('latin-1', 'replace').decode('latin-1'))
    out = REPORTS / "Mini_MRV_Report_VM0042.pdf"
    pdf.output(str(out))
    print(f"Saved report to {out}")


if __name__ == "__main__":
    build_pdf()
