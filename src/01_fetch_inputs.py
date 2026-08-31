# 01_fetch_inputs.py: fetch SoilGrids SOC (real) + NDVI proxy (mock) for Ludhiana & Karnal
# SOC: ISRIC WebDAV via rasterio /vsicurl (250m OCS 0-30cm, Homolosine projection)
# NDVI: mock per-pixel, real would be Planetary Computer STAC median composite
# Climate: mock monthly modifiers, real would be ERA5 via CDS API (needs key)
import pathlib
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds, transform as proj_transform
from shapely.geometry import box

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

DISTRICTS = {
    "Ludhiana": {"bbox": [75.4, 30.6, 76.2, 31.0], "state": "Punjab"},
    "Karnal": {"bbox": [76.4, 29.4, 77.2, 29.9], "state": "Haryana"},
}

SOILGRIDS_URL = '/vsicurl/https://files.isric.org/soilgrids/latest/data/ocs/ocs_0-30cm_mean.vrt'
PIXELS_PER_DISTRICT = 120


def make_districts():
    # bounding-box polygons for the two districts
    rows = []
    for name, meta in DISTRICTS.items():
        xmin, ymin, xmax, ymax = meta["bbox"]
        rows.append({"district": name, "state": meta["state"], "geometry": box(xmin, ymin, xmax, ymax)})
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    out = RAW / "districts.gpkg"
    try:
        gdf.to_file(out, driver="GPKG")
        print(f"Saved {out} ({len(gdf)} districts)")
    except Exception as e:
        # GDAL/pyogrio missing: fall back to WKT csv
        gdf["wkt"] = gdf.geometry.apply(lambda g: g.wkt)
        gdf.drop(columns=["geometry"]).to_csv(RAW / "districts.csv", index=False)
        print(f"GPKG failed ({e}), saved districts.csv")
    return gdf


def fetch_soc(gdf, pixels_per_district=PIXELS_PER_DISTRICT):
    # read SoilGrids 250m OCS VRT, window to each district bbox, sample ~120 pixels
    records = []
    with rasterio.open(SOILGRIDS_URL) as ds:
        for _, row in gdf.iterrows():
            xmin, ymin, xmax, ymax = row.geometry.bounds
            # bbox is WGS84 but the VRT is in Homolosine: transform before windowing
            l, b, r, t = transform_bounds('EPSG:4326', ds.crs, xmin, ymin, xmax, ymax)
            win = from_bounds(l, b, r, t, ds.transform)
            data = ds.read(1, window=win)
            wt = ds.window_transform(win)
            valid = data != ds.nodata
            stride = max(1, int(np.sqrt(valid.sum() / pixels_per_district)))
            # 2D systematic sampling: every stride-th row/col
            s_rows, s_cols = np.where(valid[::stride, ::stride])
            s_rows *= stride
            s_cols *= stride
            # pixel centers in Homolosine -> WGS84 lon/lat
            xs, ys = wt * (s_cols + 0.5, s_rows + 0.5)
            lons, lats = proj_transform(ds.crs, 'EPSG:4326', xs.tolist(), ys.tolist())
            for i in range(len(s_rows)):
                records.append({
                    "district": row["district"],
                    "lon": lons[i], "lat": lats[i],
                    "soc_0_30_tC_per_ha": float(data[s_rows[i], s_cols[i]]),
                })
    df = pd.DataFrame(records)
    out = RAW / "soc_soilgrids.csv"
    df.to_csv(out, index=False)
    print(f"SoilGrids SOC saved to {out} ({len(df)} pixels). "
          f"Means: {df.groupby('district')['soc_0_30_tC_per_ha'].mean().round(1).to_dict()}")
    return df


def calc_c_inputs(soc_df):
    # NDVI proxy for wheat biomass: real would be Planetary Computer STAC median
    np.random.seed(7)
    ndvi = np.clip(np.random.normal(0.52, 0.08, len(soc_df)), 0.30, 0.75)
    soc_df = soc_df.copy()
    soc_df["ndvi"] = ndvi
    # C input from NDVI: linear proxy, then scenario adjustments
    soc_df["c_input_retain_tC_per_ha"] = (ndvi - 0.30) * 5.5
    soc_df["c_input_burn_tC_per_ha"] = soc_df["c_input_retain_tC_per_ha"] * 0.48  # burning removes ~52% C
    soc_df["c_input_fym_tC_per_ha"] = soc_df["c_input_retain_tC_per_ha"] + 0.85  # FYM adds ~0.85 tC/ha
    soc_df[["c_input_burn_tC_per_ha", "c_input_retain_tC_per_ha", "c_input_fym_tC_per_ha"]] = soc_df[
        ["c_input_burn_tC_per_ha", "c_input_retain_tC_per_ha", "c_input_fym_tC_per_ha"]
    ].clip(lower=0.3)
    out = PROC / "c_inputs.csv"
    soc_df.to_csv(out, index=False)
    print(f"C inputs saved to {out}")
    print(soc_df[["district", "c_input_burn_tC_per_ha", "c_input_retain_tC_per_ha",
                  "c_input_fym_tC_per_ha"]].groupby("district").mean().round(2).to_string())
    return soc_df


def make_climate():
    # monthly temp/moisture modifiers for Indo-Gangetic plain: real would be ERA5 via CDS API
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    f_temp = [0.7,0.75,0.9,1.1,1.4,1.6,1.55,1.45,1.2,0.95,0.8,0.72]
    f_moist = [0.6,0.55,0.6,0.5,0.45,0.85,1.3,1.25,0.9,0.6,0.55,0.6]
    df = pd.DataFrame({"month": months, "f_temp": f_temp, "f_moist": f_moist})
    out = RAW / "climate_modifiers.csv"
    df.to_csv(out, index=False)
    print(f"Climate modifiers saved to {out}")
    return df


if __name__ == "__main__":
    print("=== 01_fetch_inputs: SoilGrids SOC + NDVI proxy ===")
    gdf = make_districts()
    soc_df = fetch_soc(gdf)
    soc_df = calc_c_inputs(soc_df)
    make_climate()
    print("Done. Next: python src/02_rothc_lite_model.py")
