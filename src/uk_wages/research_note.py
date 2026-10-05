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
    hours_heading = "Hourly pay, paid hours, and weekly earnings"
    gap_period_end = pd.Timestamp(latest_gap["date"])
    gap_period_start = gap_period_end - pd.DateOffset(months=2)
    gap_period = f"{gap_period_start:%b}-{gap_period_end:%b %Y}"
    missing_decomp_text = ", ".join(missing_decomp_groups) if missing_decomp_groups else "none"
    lines = [
        "# UK Youth Real-Wage Report",
        "",
        "## Executive Summary",
        "",
        (
            f"- The baseline 18-21 result is assessed as {verdict_18}. "
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
            "Separate medians leave an arithmetic residual, so the split remains descriptive."
        ),
        (
            f"- **ASHE publishes a 22-29 comparator.** Baseline ASHE 22-29 "
            f"real weekly earnings changed by {_fmt(ashe_22['real_pct_change'])}%, while A05 shows the 16-24 "
            f"{gap_period} unemployment gap versus 25-34 changed by {_fmt(latest_gap['youth_unemployment_gap_change_since_2019'])} "
            f"percentage points and the inactivity gap by {_fmt(latest_gap['youth_inactivity_gap_change_since_2019'])} points."
        ),
        "",
        "This note describes saved source editions. 'Latest' refers to the inputs used for this build; source releases and hashes are recorded in `config/sources.lock.yaml`. The headline compares gross earnings for employee jobs, rather than disposable household income or pay histories for the same people.",
        "",
        f"## The youngest-adult wage signal is {verdict_18}",
        "",
        (
            "ASHE is the main annual age-specific earnings source, and the baseline result uses median weekly gross "
            "earnings from the published all-sex, all-work-status employee-job rows, deflated with April CPIH. The baseline age-group changes are: "
            f"18-21 is {_fmt(ashe_18['real_pct_change'])}% from 2019 to {latest_ashe_year}, compared with "
            f"{_fmt(ashe_22['real_pct_change'])}% for 22-29, {_fmt(ashe_30['real_pct_change'])}% for 30-39, "
            f"and {_fmt(ashe_16['real_pct_change'])}% for 16-17. The strongest age group in the table is "
            f"{strongest['age_group']}, at {_fmt(strongest['real_pct_change'])}%."
        ),
        "",
        "The sensitivity count describes configured comparisons, not independent statistical trials or the probability that a claim is true. Changing the start year measures a different interval; mean earnings describe a different statistic; full-time-only rows cover a different population. The stress tests excluding 2020 from the intervening path or restricting displayed age groups preserve endpoint estimates for retained groups.",
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
        f"Report the 18-21 baseline change with its {verdict_18} assessment. Keep the source, wage measure, deflator, and worker definition attached whenever it is quoted.",
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
        "Use RTI for PAYE triangulation within the saved release's coverage, especially beyond the latest ASHE year, with its age band and monthly earnings concept attached.",
        "",
        f"## {hours_heading}",
        "",
        "The ASHE decomposition compares changes in median weekly gross pay, median hourly gross pay, and median total paid hours, retaining an arithmetic residual. These separate medians do not identify a causal mechanism.",
        "",
        (
            f"For 18-21, real weekly earnings are {_fmt(decomp_18['weekly_pct_change'])}% from 2019 to "
            f"{int(decomp_18['latest_year'])}. Real hourly pay changed by {_fmt(decomp_18['hourly_pct_change'])}%, "
            f"while total paid hours are {_fmt(decomp_18['hours_pct_change'])}%. In log terms, hourly pay contributes "
            f"{_fmt(decomp_18['hourly_log_contribution'], 3)}, hours contribute {_fmt(decomp_18['hours_log_contribution'], 3)}, "
            f"and the residual is {_fmt(decomp_18['residual_log_contribution'], 3)}. For 22-29, real weekly earnings "
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
        "For 18-21, weekly earnings and hourly pay move differently. Paid hours matter to interpretation, and the separate medians and residual limit this to a descriptive comparison.",
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
        "These composition pay changes are nominal. Published job-count ratios provide descriptive proxies for the mix of jobs; they are not weights that reconstruct an all-employee median. No composition-adjusted wage change is estimated.",
        "",
        (
            f"A05 is not an earnings source, but it shows the labour-market backdrop around young people. In {gap_period}, the "
            f"16-24 unemployment gap versus 25-34 changed by {_fmt(latest_gap['youth_unemployment_gap_change_since_2019'])} "
            f"percentage points since 2019, and the inactivity gap changed by {_fmt(latest_gap['youth_inactivity_gap_change_since_2019'])} points. "
            "The baseline is the mean of rolling periods ending in 2019. Here, 25-34 is a labour-market comparator, not an ASHE wage comparator."
        ),
        "",
        "The saved wage-floor, composition, and labour-market figures provide context. They do not identify why ASHE medians moved.",
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
        "ASHE is an April reference-period survey of employee jobs. Gross weekly earnings are before deductions and are not annual or household income. Successive age bands contain different jobs and people. Aggregate CPIH does not measure inflation specific to young people or individual households. A05 covers rolling three-month periods and is official statistics in development.",
        "",
        "Published CVs describe sampling precision. They do not rule out coverage or non-response bias; source-value checks verify selected transformations rather than survey representativeness. This project does not estimate causal effects, model student status, or quantify household living standards.",
        "",
        "## Earlier research and contribution",
        "",
        "The broad question is established. [Resolution Foundation (November 2023)](https://www.resolutionfoundation.org/comment/falling-pay-divergent-data-and-a-bulging-middle/) examines age-specific real weekly pay since 2019; its [December 2023 youth report](https://www.resolutionfoundation.org/publications/narrowing-the-youth-gap/) discusses hourly pay and hours. [Henry and Joyce (IFS, May 2024)](https://ifs.org.uk/sites/default/files/2024-05/What-has-happened-to-earnings-IFS-Report_0.pdf) compare earnings sources. [Forth and colleagues (online 2025; 2026 issue)](https://openaccess.city.ac.uk/id/eprint/35689/) examine ASHE representativeness.",
        "",
        "This is a replication and update exercise with reproducible inputs and explicit sensitivity comparisons. Earlier figures can be checked numerically only after aligning their periods, editions, populations, earnings statistics, and deflators. The project makes no claim that its broad question or descriptive hours comparison is new.",
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
