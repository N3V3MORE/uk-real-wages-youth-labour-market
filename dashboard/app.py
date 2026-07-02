from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
CHARTS = ROOT / "outputs" / "charts"
EVIDENCE = ROOT / "outputs" / "evidence"

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


main_tab, evidence_tab, methodology_tab = st.tabs(
    ["Main analysis", "Robustness and evidence", "Methodology"]
)

with main_tab:
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

with evidence_tab:
    st.header("Robustness and Evidence")
    matrix_path = EVIDENCE / "robustness_matrix.csv"
    scores_path = EVIDENCE / "fragility_scores.csv"
    one_way_path = EVIDENCE / "one_way_sensitivity.csv"
    minimal_flip_path = EVIDENCE / "minimal_flip_specs.csv"
    claims_path = EVIDENCE / "claim_assessment.csv"
    final_claims_path = EVIDENCE / "final_claims.md"
    source_checks_path = EVIDENCE / "source_value_checks.csv"
    manual_audit_path = EVIDENCE / "manual_validation_audit.md"
    contrarian_path = EVIDENCE / "contrarian_findings.md"
    if not matrix_path.exists():
        st.warning("Run `python -m uk_wages.robustness --run-all` to create evidence outputs.")
    else:
        matrix = pd.read_csv(matrix_path)
        focus = matrix[matrix["age_group"].eq("18-21")]
        spec_count = int(matrix["experiment_name"].nunique())
        supporting = int(focus["supports_main_claim"].astype(bool).sum()) if not focus.empty else 0
        reversing = int(focus["sign_flip_vs_baseline"].astype(bool).sum()) if not focus.empty else 0
        weakening = max(0, len(focus) - supporting - reversing)
        cols = st.columns(5)
        cols[0].metric("Specifications tested", spec_count)
        cols[1].metric("Supporting", supporting)
        cols[2].metric("Weakening", weakening)
        cols[3].metric("Reversing", reversing)
        if scores_path.exists():
            scores = pd.read_csv(scores_path)
            focus_score = scores[scores["age_group"].eq("18-21")]
            if "spec_tier" in scores.columns:
                all_tier_score = focus_score[focus_score["spec_tier"].eq("all")]
                if not all_tier_score.empty:
                    focus_score = all_tier_score
            if not focus_score.empty:
                cols[4].metric(
                    "Fragility score",
                    f"{focus_score.iloc[0]['fragility_score']:.1%}",
                    focus_score.iloc[0]["assessment"],
                )
        st.subheader("Robustness matrix")
        st.dataframe(matrix, use_container_width=True)
        if scores_path.exists():
            st.subheader("Fragility scores")
            st.dataframe(pd.read_csv(scores_path), use_container_width=True)
        st.subheader("Why results change")
        if one_way_path.exists():
            one_way = pd.read_csv(one_way_path)
            st.markdown("One-way sensitivity")
            st.dataframe(one_way, use_container_width=True)
        else:
            st.warning(f"Missing output: {one_way_path}")
        if minimal_flip_path.exists():
            minimal_flip = pd.read_csv(minimal_flip_path)
            st.markdown("Minimal flip diagnostics")
            st.dataframe(minimal_flip, use_container_width=True)
        else:
            st.warning(f"Missing output: {minimal_flip_path}")
        if claims_path.exists():
            st.subheader("Claim assessment")
            st.dataframe(pd.read_csv(claims_path), use_container_width=True)
        if final_claims_path.exists():
            st.subheader("Final claims")
            st.markdown(final_claims_path.read_text(encoding="utf-8"))
        st.subheader("Source validation")
        if source_checks_path.exists():
            source_checks = pd.read_csv(source_checks_path)
            st.dataframe(source_checks, use_container_width=True)
        else:
            st.warning(f"Missing output: {source_checks_path}")
        if manual_audit_path.exists():
            st.markdown(manual_audit_path.read_text(encoding="utf-8"))
    st.subheader("Contrarian findings")
    if contrarian_path.exists():
        st.markdown(contrarian_path.read_text(encoding="utf-8"))
    else:
        st.warning("Contrarian findings have not been generated yet.")

with methodology_tab:
    st.header("Methodology and Limitations")
    methodology = ROOT / "reports" / "methodology.md"
    if methodology.exists():
        st.markdown(methodology.read_text(encoding="utf-8"))
    else:
        st.warning(f"Missing methodology file: {methodology}")
