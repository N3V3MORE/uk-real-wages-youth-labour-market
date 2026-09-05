from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, project_path


OUTPUT_ROOT = project_path("outputs")
REPORTS_ROOT = project_path("reports")


def _csv(path: Path, description: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"Empty {description}: {path}")
    return frame


def _optional_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _row(frame: pd.DataFrame, column: str, value: str) -> pd.Series:
    match = frame[frame[column].astype(str).eq(value)]
    if match.empty:
        raise ValueError(f"Missing {value!r} in {column}.")
    return match.iloc[0]


def _fmt(value: object, digits: int = 2) -> str:
    if pd.isna(value):
        return "unavailable"
    return f"{float(value):.{digits}f}"


def _quality_sentence(quality: pd.DataFrame, age_group: str) -> str:
    if quality.empty:
        return "The ASHE quality audit is not available in this output set."
    focus = quality[
        quality["age_group"].astype(str).eq(age_group)
        & quality["measure"].astype(str).eq("weekly_gross")
        & quality["estimate"].astype(str).eq("median")
    ]
    if focus.empty:
        return f"The ASHE quality audit found no median weekly CV row for {age_group}."
    row = focus.iloc[0]
    return (
        f"For {age_group}, the latest ASHE median weekly CV is "
        f"{_fmt(row['latest_cv_percent'])}% "
        f"({str(row['latest_quality_status']).replace('_', ' ')})."
    )


def _composition_sentence(composition: pd.DataFrame, age_group: str) -> str:
    if composition.empty:
        return "The ASHE composition audit is not available in this output set."
    focus = composition[composition["age_group"].astype(str).eq(age_group)]
    if focus.empty:
        return f"The ASHE composition audit has no row for {age_group}."
    row = focus.iloc[0]
    return (
        f"For {age_group}, all-employee nominal weekly pay changed by "
        f"{_fmt(row['all_employee_weekly_pct_change'])}%, full-time by "
        f"{_fmt(row['full_time_weekly_pct_change'])}%, part-time by "
        f"{_fmt(row['part_time_weekly_pct_change'])}%, and paid hours by "
        f"{_fmt(row['hours_pct_change'])}%."
    )


def build_research_note(
    *,
    output_root: str | Path = OUTPUT_ROOT,
    reports_root: str | Path = REPORTS_ROOT,
) -> Path:
    output_root = Path(output_root)
    reports_root = ensure_dir(reports_root)
    tables = output_root / "tables"
    evidence = output_root / "evidence"

    ashe = _csv(tables / "age_group_real_earnings_change.csv", "ASHE age summary")
    rti = _csv(tables / "rti_age_real_pay_change.csv", "RTI age summary")
    decomp = _csv(tables / "ashe_hours_decomposition.csv", "ASHE decomposition")
    rates = _csv(tables / "minimum_wage_real_rates.csv", "minimum wage real rates")
    bite = _csv(tables / "minimum_wage_bite_by_age.csv", "minimum wage bite")
    gaps = _csv(tables / "youth_labour_market_gaps.csv", "A05 youth gap summary")
    scores = _csv(evidence / "fragility_scores.csv", "fragility scores")
    quality = _optional_csv(tables / "ashe_quality_summary.csv")
    composition = _optional_csv(tables / "ashe_composition_change_by_age.csv")

    ashe_18 = _row(ashe, "age_group", "18-21")
    ashe_22 = _row(ashe, "age_group", "22-29")
    ashe_30 = _row(ashe, "age_group", "30-39")
    ashe_16 = _row(ashe, "age_group", "16-17")
    strongest = ashe.sort_values("real_pct_change").iloc[-1]
    rti_18 = _row(rti, "age_group", "18-24")
    decomp_18 = _row(decomp, "age_group", "18-21")
    decomp_22 = _row(decomp, "age_group", "22-29")
    decomp_groups = sorted(decomp["age_group"].astype(str).unique())
    missing_decomp_groups = [
        group for group in ["18-21", "22-29", "25-34", "30-39"] if group not in decomp_groups
    ]
    latest_gap = gaps.sort_values("date").iloc[-1]
    fragility_18 = scores[
        scores["age_group"].eq("18-21") & scores["spec_tier"].eq("core")
    ].iloc[0]
    verdict_18 = str(fragility_18["assessment"]).strip().lower()
    if verdict_18 not in {"robust", "moderately robust", "fragile", "not robust", "inconclusive"}:
        raise ValueError("The 18-21 core fragility score has no assessment verdict.")

    wage_18_2019 = rates[
        rates["effective_year"].eq(2019) & rates["policy_series"].eq("18 to 20")
    ].iloc[0]
    wage_18_latest = rates[rates["policy_series"].eq("18 to 20")].sort_values("effective_year").iloc[-1]
    bite_18_2019 = bite[
        bite["year"].eq(2019) & bite["ashe_age_group"].eq("18-21")
    ].iloc[0]
    bite_18_latest = bite[bite["ashe_age_group"].eq("18-21")].sort_values("year").iloc[-1]
    bite_22_2019 = bite[
        bite["year"].eq(2019) & bite["ashe_age_group"].eq("22-29")
    ].iloc[0]
    bite_22_latest = bite[bite["ashe_age_group"].eq("22-29")].sort_values("year").iloc[-1]

    latest_ashe_year = int(ashe_18["latest_year"])
    latest_rti_month = str(rti_18["latest_available_month"])
    latest_non_flash = str(rti_18["latest_non_flash_month"])
    rti_change = float(rti_18["real_pay_pct_change_since_jan2019"])
    rti_movement = (
        f"rose by {_fmt(rti_change)}%" if rti_change > 0 else
        f"fell by {_fmt(abs(rti_change))}%" if rti_change < 0 else "was unchanged"
    )
    flash_flag = rti_18.get("latest_available_is_flash_or_provisional", pd.NA)
    flash_sentence = (
        "The latest-month flash status is unavailable in this output set."
        if pd.isna(flash_flag) else
        "The latest month is flagged as an early estimate."
        if bool(flash_flag) else "The latest month is not flagged as an early estimate."
    )
    if pd.notna(rti_18["latest_non_flash_month"]):
        flash_sentence += f" {latest_non_flash} is the latest non-flash month."
    hours_heading = (
        "Hours explain why weekly earnings can fall while hourly pay rises"
        if float(decomp_18["weekly_pct_change"]) < 0 < float(decomp_18["hourly_pct_change"])
        else "Hourly pay, paid hours, and weekly earnings"
    )
    missing_decomp_text = ", ".join(missing_decomp_groups) if missing_decomp_groups else "none"
    lines = [
        "# UK Youth Real-Wage Report",
        "",
        "## Executive Summary",
        "",
        (
            f"- **Bottom line.** The baseline 18-21 result is assessed as {verdict_18}. "
            f"Baseline ASHE shows 18-21 real median weekly earnings at {_fmt(ashe_18['real_pct_change'])}% "
            f"from 2019 to {latest_ashe_year}, but {int(fragility_18['material_disagreements'])} "
            f"of {int(fragility_18['specifications_tested'])} core robustness checks materially change the result."
        ),
        (
            f"- **The wider 18-24 monthly PAYE signal.** RTI real median monthly pay {rti_movement} "
            f"from January 2019 to {latest_rti_month}. {flash_sentence}"
        ),
        (
            f"- **Hourly pay and hours inside ASHE.** For 18-21, real hourly pay changed by "
            f"{_fmt(decomp_18['hourly_pct_change'])}%, while total paid hours are {_fmt(decomp_18['hours_pct_change'])}%; "
            "Separate medians leave a residual, so the split remains descriptive."
        ),
        (
            f"- **ASHE publishes a 22-29 comparator.** Baseline ASHE 22-29 "
            f"real weekly earnings changed by {_fmt(ashe_22['real_pct_change'])}%, while A05 shows the 16-24 "
            f"unemployment gap versus 25-34 changed by {_fmt(latest_gap['youth_unemployment_gap_change_since_2019'])} "
            f"percentage points and the inactivity gap by {_fmt(latest_gap['youth_inactivity_gap_change_since_2019'])} points."
        ),
        "",
        f"## The youngest-adult wage signal is {verdict_18}",
        "",
        (
            "ASHE is the main annual age-specific earnings source, and the baseline result uses median weekly gross "
            "earnings for all employee jobs deflated with April CPIH. The baseline age-group changes are: "
            f"18-21 is {_fmt(ashe_18['real_pct_change'])}% from 2019 to {latest_ashe_year}, compared with "
            f"{_fmt(ashe_22['real_pct_change'])}% for 22-29, {_fmt(ashe_30['real_pct_change'])}% for 30-39, "
            f"and {_fmt(ashe_16['real_pct_change'])}% for 16-17. The strongest age group in the table is "
            f"{strongest['age_group']}, at {_fmt(strongest['real_pct_change'])}%."
        ),
        "",
        (
            "The headline should still be qualified. The robustness harness changes defensible assumptions around "
            "baseline year, wage measure, deflator, worker definition, and the treatment of 2020. "
            f"For 18-21, {int(fragility_18['material_disagreements'])} of "
            f"{int(fragility_18['specifications_tested'])} core checks create material disagreements. "
            f"The baseline ASHE weekly-earnings change is {_fmt(ashe_18['real_pct_change'])}%, and the assessed robustness is {verdict_18}."
        ),
        "",
        "The practical implication is that the top-line number should not travel alone. A reader needs to see the ASHE age group, weekly-earnings measure, CPIH deflator, latest ASHE year, and robustness result next to the headline. Without that context, the baseline estimate can sound more decisive than the evidence warrants.",
        "",
        "There is no current ASHE 25-34 wage row in the processed age-specific ASHE outputs. That matters because 25-34 appears in RTI and A05, but it should not be treated as if the ASHE wage pipeline has the same age band. Where the project uses 25-34, it is using a source that actually publishes 25-34, not filling an ASHE gap.",
        "",
        _quality_sentence(quality, "18-21"),
        _quality_sentence(quality, "22-29"),
        "",
        f"**So what:** report the 18-21 baseline change with its {verdict_18} assessment. Keep the source, wage measure, deflator, and worker definition attached whenever it is quoted.",
        "",
        "## RTI extends the clock but changes the population",
        "",
        (
            f"RTI adds a monthly PAYE check through {latest_rti_month}. For 18-24, real median monthly PAYE pay is "
            f"{_fmt(rti_18['real_pay_pct_change_since_jan2019'])}% from January 2019 to {latest_rti_month}; "
            f"payrolled employees are {_fmt(rti_18['employee_count_pct_change_since_jan2019'])}% over the same baseline. "
            f"{flash_sentence}"
        ),
        "",
        "RTI adds context to the ASHE picture. RTI 18-24 overlaps ASHE 18-21 and part of ASHE 22-29; it also measures monthly PAYE pay rather than ASHE weekly earnings or hourly rates. RTI adds a separate monthly PAYE check for the wider 18-24 group; any disagreement needs to be interpreted within those source boundaries.",
        "",
        "The timing is different too. ASHE is an annual April snapshot of employee jobs, while RTI is monthly PAYE administrative data. RTI can therefore move with changes in monthly hours, job mix, bonuses, and payrolled employment during the year. That makes it valuable for recency, but it also means a monthly RTI improvement is not automatically a like-for-like correction to an annual ASHE weekly-earnings result.",
        "",
        "**So what:** use RTI for current PAYE triangulation, especially beyond the latest ASHE year, but do not treat it as the same age group or the same earnings concept.",
        "",
        f"## {hours_heading}",
        "",
        "The ASHE decomposition helps explain the ASHE weekly-earnings result by splitting weekly pay into hourly pay, paid hours, and a residual. The headline split uses gross hourly pay and total paid hours.",
        "",
        (
            f"For 18-21, real weekly earnings are {_fmt(decomp_18['weekly_pct_change'])}% from 2019 to "
            f"{int(decomp_18['latest_year'])}. Real hourly pay changed by {_fmt(decomp_18['hourly_pct_change'])}%, "
            f"while total paid hours are {_fmt(decomp_18['hours_pct_change'])}%. In log terms, hourly pay contributes "
            f"{_fmt(decomp_18['hourly_log_contribution'], 3)}, hours contribute {_fmt(decomp_18['hours_log_contribution'], 3)}, "
            f"and the residual is {_fmt(decomp_18['residual_log_contribution'], 3)}. For 22-29, real weekly earnings are "
            f"changed by {_fmt(decomp_22['weekly_pct_change'])}%, real hourly pay changed by {_fmt(decomp_22['hourly_pct_change'])}%, "
            f"and hours are {_fmt(decomp_22['hours_pct_change'])}%."
        ),
        "",
        (
            f"The computed decomposition groups in the current output are {', '.join(decomp_groups)}. "
            f"The requested groups without a computed row are {missing_decomp_text}. Those missing rows are not filled in; "
            "if ASHE Table 6 does not publish the required weekly, hourly, and hours rows for an age group, the honest output is an explicit absence."
        ),
        "",
        "The residual is important. The decomposition combines medians from separate ASHE tables, so hourly pay, paid hours, and weekly pay do not have to multiply back together exactly. The residual is the arithmetic gap left after the hourly-pay and hours movements are combined. It can reflect distributional differences across tables, changes in worker mix, or other measurement boundaries; it should not be labelled as an unexplained behavioural channel.",
        "",
        "**So what:** the weekly-pay result is not simply a pay-rate story. For 18-21, hours are central to interpretation, and the residual means the split should remain descriptive rather than causal.",
        "",
        "## Wage floors and labour-market stress add context, not causality",
        "",
        (
            f"The 18-20 statutory hourly rate moves from GBP {_fmt(wage_18_2019['nominal_hourly_rate'])} in April 2019 "
            f"to GBP {_fmt(wage_18_latest['nominal_hourly_rate'])} in April {int(wage_18_latest['effective_year'])}. After April CPIH deflation, the real statutory "
            f"wage index for 18-20 is {_fmt(wage_18_latest['real_statutory_wage_index_2019_100'])} with April 2019 set to 100. "
            f"For ASHE 18-21, the 18-20 statutory rate is {_fmt(bite_18_2019['minimum_wage_bite'], 3)} of median hourly pay in 2019 "
            f"and {_fmt(bite_18_latest['minimum_wage_bite'], 3)} in {int(bite_18_latest['year'])}. For ASHE 22-29, the adult threshold is "
            f"{_fmt(bite_22_2019['minimum_wage_bite'], 3)} of median hourly pay in 2019 and "
            f"{_fmt(bite_22_latest['minimum_wage_bite'], 3)} in {int(bite_22_latest['year'])}."
        ),
        "",
        "The minimum-wage thresholds also move over the period. ASHE 18-21 includes 21-year-olds, while the 18-20 statutory band does not. The adult threshold was 25+ before April 2021, 23+ from April 2021, and 21+ from April 2024. That shifting boundary is why the report treats minimum wage as wage-floor pressure rather than a clean treatment assignment.",
        "",
        _composition_sentence(composition, "18-21"),
        _composition_sentence(composition, "22-29"),
        "",
        (
            f"A05 is not an earnings source, but it shows the labour-market backdrop around young people. The latest output shows the "
            f"16-24 unemployment gap versus 25-34 changed by {_fmt(latest_gap['youth_unemployment_gap_change_since_2019'])} "
            f"percentage points since 2019, and the inactivity gap changed by {_fmt(latest_gap['youth_inactivity_gap_change_since_2019'])} points. "
            "Here, 25-34 is a labour-market comparator, not an ASHE wage comparator."
        ),
        "",
        "**So what:** rising statutory floors and weaker youth labour-market conditions make the context more plausible, but they do not identify why ASHE medians moved. The report should keep wage-floor, composition, and labour-market stress evidence in the supporting-evidence lane.",
        "",
        "## Recommended next steps",
        "",
        f"- **Use qualified headline wording.** Report the baseline ASHE 18-21 weekly-earnings change of {_fmt(ashe_18['real_pct_change'])}% with its {verdict_18} assessment, and keep the measure, deflator, worker definition, and baseline year visible.",
        "- **Monitor the next ASHE release first.** A clearer conclusion needs the next annual age-specific ASHE update and the same robustness harness rerun against it.",
        "- **Track RTI non-flash months separately.** RTI is useful for timeliness, but the latest flash month should not override the cleaner non-flash signal.",
        "- **Keep hours visible.** Any dashboard or brief should pair weekly earnings with hourly pay and paid-hours movement for 18-21.",
        "",
        "## Further questions",
        "",
        "- Do full-time, part-time, and sex-specific ASHE rows continue to move differently for 18-21 when the next release lands?",
        "- Does RTI 18-24 keep diverging from ASHE 18-21 once flash months are revised?",
        "- Can additional cuts such as student status, region, or occupation explain the paid-hours movement without overclaiming beyond published data?",
        "",
        "## Caveats and assumptions",
        "",
        f"ASHE remains the main annual age-specific wage source. The latest ASHE age-specific data in this output stop at {latest_ashe_year}. Monthly and contextual sources may extend further, but they do not supply later ASHE age-specific wages.",
        "",
        "The sources measure different populations, frequencies, and concepts. ASHE is an annual April snapshot of employee jobs; RTI is monthly PAYE administrative data; A05 is a rolling labour-market status table; EARN01 is whole-economy pay; and the minimum-wage series is a statutory hourly floor. The report compares them only when their boundaries remain explicit.",
        "",
        "ASHE-EARN01 comparisons use April observations for both sources and set April 2019 to 100. This avoids comparing an April snapshot with a calendar-year average or a January baseline. Differences are reported in index points; they are not differences in pay levels. Directional agreement describes overlapping adjacent years and cannot establish that the sources cover the same workers.",
        "",
        "The robustness harness tests specification sensitivity, not sampling uncertainty. It asks whether the result survives reasonable choices about baseline year, deflator, earnings measure, worker definition, and the treatment of 2020. The quality audit separately checks published ASHE CV workbooks where they exist, but it does not invent confidence intervals when the source does not provide enough evidence.",
        "",
        "This project does not estimate causal effects, does not construct ASHE confidence intervals beyond published quality markers, does not model student status or household-specific inflation, and does not use EARN01 as age-specific evidence.",
    ]
    path = reports_root / "research_note.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the v2 research note from generated outputs.")
    parser.parse_args(argv)
    print(build_research_note())


if __name__ == "__main__":
    main()
