from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
CHARTS = ROOT / "outputs" / "charts"
EVIDENCE = ROOT / "outputs" / "evidence"
REPORTS = ROOT / "reports"

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


def show_chart(title: str, image: str) -> None:
    st.subheader(title)
    path = CHARTS / image
    if path.exists():
        st.image(str(path))
    else:
        st.warning(f"Missing chart: {path}")


def show_markdown(path: Path, missing: str) -> None:
    if path.exists():
        st.markdown(path.read_text(encoding="utf-8"))
    else:
        st.warning(missing)


tabs = st.tabs(
    [
        "Headline answer",
        "ASHE",
        "Fragility",
        "RTI",
        "Decomposition",
        "Minimum wage",
        "DS upgrade",
        "Labour-market stress",
        "Validation",
    ]
)

with tabs[0]:
    st.header("Did young workers clearly get better or worse off?")
    final_claims = EVIDENCE / "final_claims.md"
    if final_claims.exists():
        st.markdown(final_claims.read_text(encoding="utf-8"))
    else:
        summary = read_csv("age_group_real_earnings_change.csv")
        if not summary.empty:
            st.dataframe(summary, width="stretch")
        st.warning("Run the evidence step to create final claim wording.")

with tabs[1]:
    st.header("What does the main annual wage source say?")
    summary = read_csv("age_group_real_earnings_change.csv")
    if not summary.empty:
        latest_year = int(summary["latest_year"].max())
        st.metric("Latest age-specific ASHE year", latest_year)
        st.dataframe(summary, width="stretch")
    show_chart("Real earnings by age group", "real_earnings_by_age.png")
    show_chart("Real earnings change since 2019", "real_earnings_change_by_age.png")
    show_chart("Regional young-worker comparison", "young_worker_real_earnings_by_region.png")

with tabs[2]:
    st.header("Does the answer survive reasonable assumptions?")
    matrix_path = EVIDENCE / "robustness_matrix.csv"
    scores_path = EVIDENCE / "fragility_scores.csv"
    one_way_path = EVIDENCE / "one_way_sensitivity.csv"
    minimal_flip_path = EVIDENCE / "minimal_flip_specs.csv"
    claims_path = EVIDENCE / "claim_assessment.csv"
    contrarian_path = EVIDENCE / "contrarian_findings.md"
    if not matrix_path.exists():
        st.warning("Run the robustness step to create evidence outputs.")
    else:
        matrix = pd.read_csv(matrix_path)
        focus = matrix[matrix["age_group"].eq("18-21")]
        spec_count = int(matrix["experiment_name"].nunique())
        supporting = int(focus["supports_main_claim"].astype(bool).sum()) if not focus.empty else 0
        reversing = int(focus["sign_flip_vs_baseline"].astype(bool).sum()) if not focus.empty else 0
        weakening = max(0, len(focus) - supporting - reversing)
        cols = st.columns(4)
        cols[0].metric("Specifications tested", spec_count)
        cols[1].metric("Supporting", supporting)
        cols[2].metric("Weakening", weakening)
        cols[3].metric("Reversing", reversing)
        if scores_path.exists():
            st.subheader("Fragility scores")
            st.dataframe(pd.read_csv(scores_path), width="stretch")
        st.subheader("Robustness matrix")
        st.dataframe(matrix, width="stretch")
        if one_way_path.exists():
            st.subheader("One-way sensitivity")
            st.dataframe(pd.read_csv(one_way_path), width="stretch")
        if minimal_flip_path.exists():
            st.subheader("Minimal flip diagnostics")
            st.dataframe(pd.read_csv(minimal_flip_path), width="stretch")
        if claims_path.exists():
            st.subheader("Claim assessment")
            st.dataframe(pd.read_csv(claims_path), width="stretch")
    st.subheader("Contrarian findings")
    show_markdown(contrarian_path, "Contrarian findings have not been generated yet.")

with tabs[3]:
    st.header("Does monthly PAYE age data tell the same story?")
    rti_summary = read_csv("rti_age_real_pay_change.csv")
    if not rti_summary.empty:
        st.dataframe(rti_summary, width="stretch")
    annual_rti = EVIDENCE / "rti_ashe_annual_summary.csv"
    if annual_rti.exists():
        st.subheader("April-to-April RTI-ASHE concordance")
        st.dataframe(pd.read_csv(annual_rti), width="stretch")
    show_chart("RTI real median monthly PAYE pay", "rti_real_median_monthly_pay_by_age.png")
    show_chart("RTI payrolled employees", "rti_payrolled_employees_by_age.png")
    show_markdown(
        EVIDENCE / "rti_ashe_triangulation.md",
        "Run RTI triangulation to create the source-bounded comparison.",
    )

with tabs[4]:
    st.header("Is weekly pay moving because hourly pay changed or because hours changed?")
    decomp = read_csv("ashe_hours_decomposition.csv")
    if not decomp.empty:
        st.dataframe(decomp, width="stretch")
    decomp_time = read_csv("ashe_hours_decomposition_timeseries.csv")
    if not decomp_time.empty:
        st.subheader("Year-by-year decomposition")
        st.dataframe(decomp_time, width="stretch")
    show_chart("Weekly pay decomposition", "weekly_pay_decomposition_by_age.png")
    show_markdown(
        EVIDENCE / "ashe_decomposition_report.md",
        "Run ASHE decomposition to create the availability and decomposition report.",
    )

with tabs[5]:
    st.header("Did statutory wage floors change enough to matter?")
    rates = read_csv("minimum_wage_real_rates.csv")
    if not rates.empty:
        st.dataframe(rates, width="stretch")
    bite = read_csv("minimum_wage_bite_by_age.csv")
    if not bite.empty:
        st.subheader("Minimum wage bite")
        st.dataframe(bite, width="stretch")
    show_chart("Real minimum wage by age", "real_minimum_wage_by_age.png")
    show_chart("Minimum wage bite", "minimum_wage_bite_young_workers.png")
    show_markdown(
        EVIDENCE / "minimum_wage_context.md",
        "Run the minimum wage context step to create the report.",
    )

with tabs[6]:
    st.header("What modelling diagnostics were added for Option B?")
    structural = read_csv("structural_break_weights.csv")
    if not structural.empty:
        st.subheader("Structural-break relative-weight screen")
        st.dataframe(structural, width="stretch")
    event_study = read_csv("minimum_wage_event_study.csv")
    if not event_study.empty:
        st.subheader("Minimum-wage event framing")
        st.dataframe(event_study, width="stretch")
    forecast = read_csv("ashe_forecast_baseline.csv")
    if not forecast.empty:
        st.subheader("Forecast baseline with rough residual bands")
        st.dataframe(forecast, width="stretch")
    show_markdown(
        EVIDENCE / "option_b_ds_report.md",
        "Option B data-science report is missing.",
    )

with tabs[7]:
    st.header("Were young people also facing worse labour-market stress?")
    gaps = read_csv("youth_labour_market_gaps.csv")
    if not gaps.empty:
        st.dataframe(gaps.tail(20), width="stretch")
    show_chart("Youth unemployment and inactivity", "youth_labour_market_stress.png")

with tabs[8]:
    st.header("Can we trust the data pipeline?")
    source_checks_path = EVIDENCE / "source_value_checks.csv"
    if source_checks_path.exists():
        checks = pd.read_csv(source_checks_path)
        st.dataframe(checks, width="stretch")
    else:
        st.warning(f"Missing output: {source_checks_path}")
    st.subheader("ASHE uncertainty and quality")
    quality = read_csv("ashe_quality_summary.csv")
    if not quality.empty:
        st.dataframe(quality, width="stretch")
    show_markdown(
        EVIDENCE / "ashe_quality_availability.md",
        "ASHE quality availability audit is missing.",
    )
    show_markdown(
        EVIDENCE / "ashe_uncertainty_bands.md",
        "ASHE approximate CV-band report is missing.",
    )
    triangulation_summary = EVIDENCE / "triangulation_summary.csv"
    if triangulation_summary.exists():
        st.subheader("ASHE-EARN01 triangulation")
        st.dataframe(pd.read_csv(triangulation_summary), width="stretch")
    st.subheader("ASHE composition")
    composition = read_csv("ashe_composition_change_by_age.csv")
    if not composition.empty:
        st.dataframe(composition, width="stretch")
    show_markdown(
        EVIDENCE / "ashe_composition_audit.md",
        "ASHE composition audit is missing.",
    )
    st.subheader("Claim confidence")
    confidence_path = EVIDENCE / "claim_confidence_ladder.csv"
    if confidence_path.exists():
        st.dataframe(pd.read_csv(confidence_path), width="stretch")
    show_markdown(EVIDENCE / "claim_confidence.md", "Claim confidence ladder is missing.")
    st.subheader("Headline number lineage")
    lineage_path = EVIDENCE / "headline_number_lineage.csv"
    if lineage_path.exists():
        st.dataframe(pd.read_csv(lineage_path), width="stretch")
    show_markdown(EVIDENCE / "headline_number_lineage.md", "Headline lineage report is missing.")
    show_markdown(EVIDENCE / "manual_validation_audit.md", "Manual validation audit is missing.")
    show_markdown(REPORTS / "methodology.md", "Methodology file is missing.")
