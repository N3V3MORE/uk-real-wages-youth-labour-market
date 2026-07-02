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


def _row(frame: pd.DataFrame, column: str, value: str) -> pd.Series:
    match = frame[frame[column].astype(str).eq(value)]
    if match.empty:
        raise ValueError(f"Missing {value!r} in {column}.")
    return match.iloc[0]


def _fmt(value: object, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}"


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

    wage_18_2019 = rates[
        rates["effective_year"].eq(2019) & rates["policy_series"].eq("18 to 20")
    ].iloc[0]
    wage_18_2026 = rates[
        rates["effective_year"].eq(2026) & rates["policy_series"].eq("18 to 20")
    ].iloc[0]
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
    lines = [
        "# Real Wages and Youth Labour Market Stress in the UK, 2019-2026",
        "",
        "## 1. Short Answer",
        "",
        (
            "The 18-21 real-wage result is still not a clean win or loss. "
            f"In the baseline ASHE run, median weekly earnings for 18-21 year-olds are "
            f"{_fmt(ashe_18['real_pct_change'])}% in real CPIH terms from 2019 to {latest_ashe_year}. "
            f"That finding is fragile: {int(fragility_18['material_disagreements'])} of "
            f"{int(fragility_18['specifications_tested'])} core robustness checks create a material disagreement."
        ),
        "",
        (
            f"RTI monthly PAYE data shows 18-24 median monthly pay {_fmt(rti_18['real_pay_pct_change_since_jan2019'])}% "
            f"from January 2019 to {latest_rti_month}, although that latest month is flagged as an early estimate. "
            "The ASHE decomposition shows the accounting split behind the tension: for 18-21 year-olds, real hourly pay rose, "
            "but total paid hours fell sharply."
        ),
        "",
        (
            f"The 22-29 ASHE result is steadier. Baseline real weekly earnings are up {_fmt(ashe_22['real_pct_change'])}% "
            f"from 2019 to {latest_ashe_year}, and the decomposition shows hourly pay doing most of the work. "
            f"A05 shows the 16-24 unemployment gap has widened by {_fmt(latest_gap['youth_unemployment_gap_change_since_2019'])} "
            f"percentage points versus 25-34 since 2019; the inactivity gap has widened by "
            f"{_fmt(latest_gap['youth_inactivity_gap_change_since_2019'])} points."
        ),
        "",
        "## 2. Why This Is Hard To Answer",
        "",
        "ASHE is the strongest source for annual age-specific earnings, but the current ASHE age-specific data stop at 2025 provisional. The project title includes 2026 because other sources extend into 2026, not because ASHE provides 2026 age-specific wages.",
        "",
        "RTI gives a more current monthly view and includes age bands, but it is PAYE administrative data. It covers payrolled employees, excludes self-employment income, and measures monthly pay. That is useful triangulation, but it is not the same thing as ASHE weekly earnings.",
        "",
        "Age bands also do not line up neatly. RTI has 18-24. ASHE has 18-21 and 22-29. Minimum wage policy uses thresholds such as 18-20, 21+, 23+, and 25+. A single age label can therefore mix workers facing different policy rules, different hours, and different work patterns.",
        "",
        "Weekly earnings combine hourly pay and hours worked. If hourly pay rises while paid hours fall, weekly earnings can look flat or negative. That is why the v2 pipeline adds the ASHE hourly-pay and hours decomposition.",
        "",
        "The measures also use different clocks. ASHE is an annual April snapshot of employee jobs. RTI is monthly PAYE administrative data, so it can move with changes in hours, job mix, bonuses, and payrolled employment during the year. A05 is a rolling labour-market status table, not a pay table. The minimum-wage series is a statutory hourly floor. Putting those sources side by side is useful only if each one keeps its own job.",
        "",
        "## 3. ASHE Baseline Result",
        "",
        "The baseline ASHE result uses median weekly gross earnings for all employee jobs and deflates them with April CPIH.",
        "",
        f"- 18-21 real median weekly earnings are {_fmt(ashe_18['real_pct_change'])}%.",
        f"- 22-29 real median weekly earnings are up {_fmt(ashe_22['real_pct_change'])}%.",
        f"- 30-39 real median weekly earnings are up {_fmt(ashe_30['real_pct_change'])}%.",
        f"- 16-17 real median weekly earnings are up {_fmt(ashe_16['real_pct_change'])}%.",
        f"- {strongest['age_group']} is the strongest age group in the baseline table, up {_fmt(strongest['real_pct_change'])}%.",
        "",
        "So the narrow ASHE baseline says the youngest adult group is the weak spot. It does not say that all younger workers lost ground. It also does not say anything about 2026 age-specific ASHE wages.",
        "",
        "There is also no current ASHE 25-34 wage row in the processed age-specific ASHE outputs. That matters because 25-34 appears in RTI and A05, but it should not be treated as if the ASHE wage pipeline has the same age band. Where the project uses 25-34, it is using a source that actually publishes 25-34, not filling an ASHE gap.",
        "",
        "## 4. Why The 18-21 Result Is Fragile",
        "",
        (
            "The robustness harness changes defensible assumptions: baseline year, wage measure, deflator, worker definition, and the treatment of 2020. "
            f"For 18-21, {int(fragility_18['material_disagreements'])} of {int(fragility_18['specifications_tested'])} core checks create material disagreements."
        ),
        "",
        "The baseline result is small enough to move. Do not say 18-21 workers clearly became worse off. Say this instead: on the baseline ASHE weekly-earnings measure, 18-21 is down, but the direction and size are specification-dependent.",
        "",
        "This is specification sensitivity, not sampling uncertainty. The harness asks whether the conclusion survives reasonable choices about baseline year, deflator, earnings measure, worker definition, and the treatment of 2020. It does not estimate confidence intervals for ASHE medians, and it does not use ASHE quality flags to draw uncertainty bands. The output should therefore be read as a robustness audit of the modelling choices made here.",
        "",
        "## 5. What RTI Adds",
        "",
        (
            f"RTI adds a monthly PAYE check that reaches into 2026. For 18-24, real median monthly PAYE pay is "
            f"{_fmt(rti_18['real_pay_pct_change_since_jan2019'])}% from January 2019 to {latest_rti_month}. "
            f"The same RTI row shows payrolled employees {_fmt(rti_18['employee_count_pct_change_since_jan2019'])}% from January 2019. "
            f"The latest available month is flagged as an early estimate; {latest_non_flash} is the latest non-flash month in the current output."
        ),
        "",
        "This complicates the ASHE picture rather than replacing it. RTI 18-24 overlaps ASHE 18-21 and part of ASHE 22-29. It also captures monthly PAYE pay, not weekly earnings or hourly rates.",
        "",
        "The latest RTI month is useful because it reaches beyond ASHE, but it should carry less weight than the non-flash months. The current report keeps both dates visible for that reason: the latest available month shows the most current PAYE signal, while the latest non-flash month is the cleaner check against revision-prone data. Neither date turns RTI into an ASHE substitute.",
        "",
        "## 6. Hourly Pay Versus Hours",
        "",
        "The decomposition reads ASHE weekly gross pay, hourly gross pay, hourly pay excluding overtime, total paid hours, and basic paid hours. The headline split uses gross hourly pay and total paid hours.",
        "",
        (
            f"For 18-21, real weekly earnings are {_fmt(decomp_18['weekly_pct_change'])}% from 2019 to {int(decomp_18['latest_year'])}. "
            f"Real hourly pay is up {_fmt(decomp_18['hourly_pct_change'])}%, while total paid hours are {_fmt(decomp_18['hours_pct_change'])}%. "
            f"In log terms, hourly pay contributes {_fmt(decomp_18['hourly_log_contribution'], 3)}, "
            f"hours contribute {_fmt(decomp_18['hours_log_contribution'], 3)}, and the residual is {_fmt(decomp_18['residual_log_contribution'], 3)}."
        ),
        "",
        (
            f"For 22-29, real weekly earnings are up {_fmt(decomp_22['weekly_pct_change'])}%, "
            f"real hourly pay is up {_fmt(decomp_22['hourly_pct_change'])}%, and hours are {_fmt(decomp_22['hours_pct_change'])}%."
        ),
        "",
        (
            f"The computed decomposition groups in the current output are {', '.join(decomp_groups)}. "
            f"The requested groups without a computed decomposition row are {', '.join(missing_decomp_groups) if missing_decomp_groups else 'none'}. "
            "Those missing rows are not filled in. If ASHE Table 6 does not publish the required weekly, hourly, and hours rows for an age group in this pipeline, the honest output is an explicit absence, not an invented estimate."
        ),
        "",
        "This is still not causal. The decomposition uses medians from separate ASHE tables, so the residual matters. The residual is the arithmetic gap left after combining the median hourly-pay movement and median-hours movement. It can reflect the fact that the medians come from different distributions and tables; it should not be read as an unexplained behavioural channel.",
        "",
        "## 7. Minimum Wage Context",
        "",
        (
            f"The 18-20 statutory hourly rate rises from GBP {_fmt(wage_18_2019['nominal_hourly_rate'])} in April 2019 "
            f"to GBP {_fmt(wage_18_2026['nominal_hourly_rate'])} in April 2026. After April CPIH deflation, "
            f"the real statutory wage index for 18-20 is {_fmt(wage_18_2026['real_statutory_wage_index_2019_100'])} with April 2019 set to 100."
        ),
        "",
        (
            f"For ASHE 18-21, the 18-20 statutory rate is {_fmt(bite_18_2019['minimum_wage_bite'], 3)} of median hourly pay in 2019 "
            f"and {_fmt(bite_18_latest['minimum_wage_bite'], 3)} in {int(bite_18_latest['year'])}. "
            f"For ASHE 22-29, the adult statutory threshold is {_fmt(bite_22_2019['minimum_wage_bite'], 3)} of median hourly pay in 2019 "
            f"and {_fmt(bite_22_latest['minimum_wage_bite'], 3)} in {int(bite_22_latest['year'])}."
        ),
        "",
        "Those numbers are context, not causality. ASHE 18-21 includes 21-year-olds, while the 18-20 statutory band does not. The adult threshold also changes over time: 25+ before April 2021, 23+ from April 2021, and 21+ from April 2024.",
        "",
        "That shifting threshold is why the minimum-wage section is deliberately framed as wage-floor pressure rather than a causal estimate. A rising statutory floor can make the youth-wage story more plausible, but the tables here do not identify who was paid the floor, how many hours they worked, or whether an observed ASHE median changed because of policy, composition, or hours.",
        "",
        "## 8. Youth Labour-Market Stress",
        "",
        (
            f"A05 is not an earnings source, but it helps describe labour-market pressure around young people. "
            f"The latest A05 output shows the 16-24 unemployment gap versus 25-34 has widened by "
            f"{_fmt(latest_gap['youth_unemployment_gap_change_since_2019'])} percentage points since 2019. "
            f"The inactivity gap has widened by {_fmt(latest_gap['youth_inactivity_gap_change_since_2019'])} percentage points."
        ),
        "",
        "Here, 25-34 is a labour-market comparator, not an ASHE wage comparator. A05 publishes the 25-34 status group, so it is a reasonable benchmark for youth unemployment and inactivity gaps. That does not create a matching ASHE 25-34 wage estimate, and it does not mean the A05 gap explains the wage result. It simply says the broader youth labour-market backdrop has become more strained relative to the next older group.",
        "",
        "## 9. What We Can And Cannot Conclude",
        "",
        "What the evidence supports:",
        "",
        "- ASHE remains the main annual age-specific wage source.",
        f"- Baseline ASHE 18-21 real weekly earnings are {_fmt(ashe_18['real_pct_change'])}% from 2019 to {latest_ashe_year}.",
        "- The 18-21 result is fragile under reasonable specification changes.",
        "- The ASHE decomposition shows 18-21 hourly pay rising while paid hours fall.",
        "- RTI provides monthly PAYE age-pay triangulation into 2026.",
        "- Minimum wage rates rose materially in real terms for young age thresholds.",
        "",
        "Things this project does not prove:",
        "",
        "- It does not estimate causal effects.",
        "- It does not estimate ASHE sampling uncertainty or publish uncertainty intervals.",
        "- It does not claim ASHE 2026 age-specific wages.",
        "- It does not model student status, local authority differences, or household-specific inflation.",
        "- It does not use EARN01 as age-specific evidence.",
        "",
        "## 10. Final Answer",
        "",
        "I would not sell this as a clean youth wage gain or loss. Baseline ASHE says 18-21 real weekly earnings fell slightly from 2019 to 2025, but that result is fragile. RTI says broader 18-24 monthly PAYE pay rose in real terms into 2026. The ASHE decomposition shows how both can be true in the published medians: for 18-21, hourly pay rose, but hours fell enough to pull weekly earnings down. Minimum wage policy gives wage-floor context, and A05 shows youth labour-market stress has worsened.",
        "",
        "So the v2 conclusion is not that young workers simply got better off or worse off. It is that the youth real-wage story is mixed, source-dependent, and strongly affected by hours.",
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
