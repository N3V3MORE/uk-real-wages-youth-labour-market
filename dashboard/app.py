from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from uk_wages.dashboard_logic import robustness_headline_metrics


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
CHARTS = ROOT / "outputs" / "charts"
EVIDENCE = ROOT / "outputs" / "evidence"
REPORTS = ROOT / "reports"

st.set_page_config(page_title="UK Real Wages", layout="wide")
st.title("Real Wages and Youth Labour Market Stress in the UK")
st.caption(
    "Archived release: ASHE 2019-2025 (2025 provisional); June 2026 monthly source editions. "
    "RTI ends May 2026 (early/flash), EARN01 April 2026, A05 February-April 2026. "
    "Gross employee-job earnings do not measure household living standards."
)
st.caption("Download CSV below each table includes all columns in the original row order.")


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


def show_table(frame: pd.DataFrame, filename: str) -> None:
    st.dataframe(frame, width="stretch")
    st.download_button(
        "Download CSV",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=f"csv_{filename}",
        on_click="ignore",
    )


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
    st.header("How did young employee jobs' real weekly pay change?")
    final_claims = EVIDENCE / "final_claims.md"
    if final_claims.exists():
        st.markdown(final_claims.read_text(encoding="utf-8"))
    else:
        summary = read_csv("age_group_real_earnings_change.csv")
        if not summary.empty:
            show_table(summary, "headline_age_group_real_earnings_change.csv")
        st.warning("Run the evidence step to create final claim wording.")

with tabs[1]:
    st.header("What does the main annual wage source say?")
    summary = read_csv("age_group_real_earnings_change.csv")
    if not summary.empty:
        latest_year = int(summary["latest_year"].max())
        st.metric("Latest age-specific ASHE year", latest_year)
        show_table(summary, "age_group_real_earnings_change.csv")
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
        if scores_path.exists():
            scores = pd.read_csv(scores_path)
            headline = robustness_headline_metrics(matrix, scores)
            cols = st.columns(6)
            cols[0].metric("Core alternatives tested", headline["alternatives_tested"])
            cols[1].metric("Supporting alternatives", headline["supporting_alternatives"])
            cols[2].metric("Weakening alternatives", headline["weakening_alternatives"])
            cols[3].metric("Reversing alternatives", headline["reversing_alternatives"])
            cols[4].metric(
                "18-21 material disagreements",
                f"{headline['material_disagreements']} of {headline['alternatives_tested']}",
            )
            cols[5].metric("18-21 core verdict", headline["assessment"])
            st.subheader("Fragility scores")
            show_table(scores, "fragility_scores.csv")
        else:
            st.warning("Fragility scores have not been generated yet.")
        st.subheader("Robustness matrix")
        show_table(matrix, "robustness_matrix.csv")
        if one_way_path.exists():
            st.subheader("One-way sensitivity")
            show_table(pd.read_csv(one_way_path), "one_way_sensitivity.csv")
        if minimal_flip_path.exists():
            st.subheader("Minimal material-change diagnostics")
            st.caption("A material disagreement can change magnitude while keeping the same sign.")
            show_table(
                pd.read_csv(minimal_flip_path).rename(columns={
                    "material_flip": "material_disagreement",
                    "flipped_result": "alternative_result",
                }),
                "minimal_material_change_diagnostics.csv",
            )
        if claims_path.exists():
            st.subheader("Claim assessment")
            show_table(pd.read_csv(claims_path), "claim_assessment.csv")
    st.subheader("Contrarian findings")
    show_markdown(contrarian_path, "Contrarian findings have not been generated yet.")

with tabs[3]:
    st.header("Does monthly PAYE age data tell the same story?")
    rti_summary = read_csv("rti_age_real_pay_change.csv")
    if not rti_summary.empty:
        show_table(rti_summary, "rti_age_real_pay_change.csv")
    annual_rti = EVIDENCE / "rti_ashe_annual_summary.csv"
    if annual_rti.exists():
        st.subheader("April-to-April RTI-ASHE concordance")
        show_table(pd.read_csv(annual_rti), "rti_ashe_annual_summary.csv")
    show_chart("RTI real median monthly PAYE pay", "rti_real_median_monthly_pay_by_age.png")
    show_chart("RTI payrolled employees", "rti_payrolled_employees_by_age.png")
    show_markdown(
        EVIDENCE / "rti_ashe_triangulation.md",
        "Run RTI triangulation to create the source-bounded comparison.",
    )

with tabs[4]:
    st.header("How do weekly pay, hourly pay and paid hours compare?")
    st.caption("Separate medians give a descriptive accounting comparison, not a causal explanation.")
    decomp = read_csv("ashe_hours_decomposition.csv")
    if not decomp.empty:
        show_table(decomp, "ashe_hours_decomposition.csv")
    decomp_time = read_csv("ashe_hours_decomposition_timeseries.csv")
    if not decomp_time.empty:
        st.subheader("Year-by-year decomposition")
        show_table(decomp_time, "ashe_hours_decomposition_timeseries.csv")
    show_chart("Weekly pay decomposition", "weekly_pay_decomposition_by_age.png")
    show_markdown(
        EVIDENCE / "ashe_decomposition_report.md",
        "Run ASHE decomposition to create the availability and decomposition report.",
    )

with tabs[5]:
    st.header("Did statutory wage floors change enough to matter?")
    rates = read_csv("minimum_wage_real_rates.csv")
    if not rates.empty:
        show_table(rates, "minimum_wage_real_rates.csv")
    bite = read_csv("minimum_wage_bite_by_age.csv")
    if not bite.empty:
        st.subheader("Minimum wage bite")
        show_table(bite, "minimum_wage_bite_by_age.csv")
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
        show_table(structural, "structural_break_weights.csv")
    event_study = read_csv("minimum_wage_event_study.csv")
    if not event_study.empty:
        st.subheader("Minimum-wage event framing")
        show_table(event_study, "minimum_wage_event_study.csv")
    forecast = read_csv("ashe_forecast_baseline.csv")
    if not forecast.empty:
        st.subheader("Forecast baseline with rough residual bands")
        show_table(forecast, "ashe_forecast_baseline.csv")
    show_markdown(
        EVIDENCE / "option_b_ds_report.md",
        "Option B data-science report is missing.",
    )

with tabs[7]:
    st.header("Were young people also facing worse labour-market stress?")
    gaps = read_csv("youth_labour_market_gaps.csv")
    if not gaps.empty:
        show_table(gaps.tail(20), "youth_labour_market_gaps_latest_20.csv")
    show_chart("Youth unemployment and inactivity", "youth_labour_market_stress.png")

with tabs[8]:
    st.header("Can we trust the data pipeline?")
    source_checks_path = EVIDENCE / "source_value_checks.csv"
    if source_checks_path.exists():
        checks = pd.read_csv(source_checks_path)
        show_table(checks, "source_value_checks.csv")
    else:
        st.warning(f"Missing output: {source_checks_path}")
    st.subheader("ASHE uncertainty and quality")
    quality = read_csv("ashe_quality_summary.csv")
    if not quality.empty:
        show_table(quality, "ashe_quality_summary.csv")
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
        show_table(pd.read_csv(triangulation_summary), "triangulation_summary.csv")
    st.subheader("ASHE composition")
    composition = read_csv("ashe_composition_change_by_age.csv")
    if not composition.empty:
        show_table(composition, "ashe_composition_change_by_age.csv")
    show_markdown(
        EVIDENCE / "ashe_composition_audit.md",
        "ASHE composition audit is missing.",
    )
    st.subheader("Claim confidence")
    confidence_path = EVIDENCE / "claim_confidence_ladder.csv"
    if confidence_path.exists():
        show_table(pd.read_csv(confidence_path), "claim_confidence_ladder.csv")
    show_markdown(EVIDENCE / "claim_confidence.md", "Claim confidence ladder is missing.")
    st.subheader("Headline number lineage")
    lineage_path = EVIDENCE / "headline_number_lineage.csv"
    if lineage_path.exists():
        show_table(pd.read_csv(lineage_path), "headline_number_lineage.csv")
    show_markdown(EVIDENCE / "headline_number_lineage.md", "Headline lineage report is missing.")
    show_markdown(EVIDENCE / "manual_validation_audit.md", "Manual validation audit is missing.")
    show_markdown(REPORTS / "methodology.md", "Methodology file is missing.")
