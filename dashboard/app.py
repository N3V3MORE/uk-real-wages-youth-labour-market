from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
CHARTS = ROOT / "outputs" / "charts"

st.set_page_config(page_title="UK Real Wages", layout="wide")
st.title("Real Wages and Youth Labour Market Stress in the UK")


def read_csv(name: str) -> pd.DataFrame:
    path = TABLES / name
    if not path.exists():
        st.warning(f"Missing output: {path}")
        return pd.DataFrame()
    return pd.read_csv(path)


def read_parquet(name: str) -> pd.DataFrame:
    path = PROCESSED / name
    if not path.exists():
        st.warning(f"Missing processed file: {path}")
        return pd.DataFrame()
    return pd.read_parquet(path)


summary = read_csv("age_group_real_earnings_change.csv")
if not summary.empty:
    latest_year = int(summary["latest_year"].max())
    avg_change = summary["real_pct_change"].mean()
    st.metric("Latest age-specific ASHE year", latest_year)
    st.metric("Average real change across age groups", f"{avg_change:.1f}%")
    st.dataframe(summary, use_container_width=True)

for title, image in [
    ("Real earnings by age group", "real_earnings_by_age.png"),
    ("Regional young-worker comparison", "young_worker_real_earnings_by_region.png"),
    ("Youth unemployment and inactivity", "youth_labour_market_stress.png"),
    ("Monthly real wage trend", "monthly_real_awe.png"),
]:
    st.header(title)
    path = CHARTS / image
    if path.exists():
        st.image(str(path))
    else:
        st.warning(f"Missing chart: {path}")

st.header("Methodology and Limitations")
methodology = ROOT / "reports" / "methodology.md"
if methodology.exists():
    st.markdown(methodology.read_text(encoding="utf-8"))
else:
    st.warning(f"Missing methodology file: {methodology}")

