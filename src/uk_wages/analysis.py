from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import load_yaml, project_path, write_dataframe


PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_TABLES = project_path("outputs", "tables")
ANALYSIS_CONFIG = project_path("config", "analysis.yaml")


def real_wage_index(nominal_earnings_index: float, price_index: float) -> float:
    return nominal_earnings_index / price_index * 100


def _filter_main_ashe(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    ashe_config = config["ashe"]
    return df[
        df["earnings_measure"].eq(ashe_config["preferred_measure"])
        & df["sex"].eq(ashe_config["default_sex"])
        & df["work_status"].eq(ashe_config["default_work_status"])
        & ~df["age_group"].eq("All employees")
    ].copy()


def compute_real_earnings_by_age(
    ashe: pd.DataFrame,
    inflation_annual: pd.DataFrame,
    *,
    baseline_year: int = 2019,
) -> pd.DataFrame:
    price = inflation_annual[["year", "cpih_index_2019_100", "cpi_index_2019_100"]]
    joined = ashe.merge(price, on="year", how="inner")
    base = (
        joined[joined["year"].eq(baseline_year)]
        .set_index("age_group")["nominal_earnings"]
        .to_dict()
    )
    joined = joined[joined["age_group"].isin(base)].copy()
    joined["nominal_earnings_index_2019_100"] = joined.apply(
        lambda row: row["nominal_earnings"] / base[row["age_group"]] * 100,
        axis=1,
    )
    joined["real_earnings_index_2019_100"] = (
        joined["nominal_earnings_index_2019_100"] / joined["cpih_index_2019_100"] * 100
    )
    joined["real_earnings_index_cpi_2019_100"] = (
        joined["nominal_earnings_index_2019_100"] / joined["cpi_index_2019_100"] * 100
    )
    joined["nominal_pct_change_since_2019"] = joined["nominal_earnings_index_2019_100"] - 100
    joined["inflation_pct_change_since_2019"] = joined["cpih_index_2019_100"] - 100
    joined["real_pct_change_since_2019"] = joined["real_earnings_index_2019_100"] - 100
    joined["real_pct_change_cpi_since_2019"] = joined["real_earnings_index_cpi_2019_100"] - 100
    return joined.sort_values(["age_group", "year"]).reset_index(drop=True)


def summarise_age_changes(real_age: pd.DataFrame, *, baseline_year: int = 2019) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for age_group, group in real_age.groupby("age_group"):
        ordered = group.sort_values("year")
        base = ordered[ordered["year"].eq(baseline_year)].iloc[0]
        latest = ordered.iloc[-1]
        real_change = latest["real_pct_change_since_2019"]
        rows.append(
            {
                "age_group": age_group,
                "latest_year": int(latest["year"]),
                "nominal_earnings_2019": round(float(base["nominal_earnings"]), 2),
                "nominal_earnings_latest": round(float(latest["nominal_earnings"]), 2),
                "nominal_pct_change": round(float(latest["nominal_pct_change_since_2019"]), 2),
                "inflation_pct_change": round(float(latest["inflation_pct_change_since_2019"]), 2),
                "real_pct_change": round(float(real_change), 2),
                "real_pct_change_cpi_deflator": round(
                    float(latest["real_pct_change_cpi_since_2019"]), 2
                ),
                "real_gain_or_loss": "gain" if real_change > 0 else "loss" if real_change < 0 else "flat",
            }
        )
    return pd.DataFrame(rows).sort_values("age_group").reset_index(drop=True)


def compute_region_age_changes(
    region_ashe: pd.DataFrame,
    inflation_annual: pd.DataFrame,
    *,
    baseline_year: int = 2019,
) -> pd.DataFrame:
    price = inflation_annual[["year", "cpih_index_2019_100"]]
    joined = region_ashe.merge(price, on="year", how="inner")
    keys = ["region", "age_group"]
    base = (
        joined[joined["year"].eq(baseline_year)]
        .set_index(keys)["nominal_earnings"]
        .to_dict()
    )
    joined = joined[joined.set_index(keys).index.isin(base)].copy()
    joined["nominal_earnings_index_2019_100"] = joined.apply(
        lambda row: row["nominal_earnings"] / base[(row["region"], row["age_group"])] * 100,
        axis=1,
    )
    joined["real_earnings_index_2019_100"] = (
        joined["nominal_earnings_index_2019_100"] / joined["cpih_index_2019_100"] * 100
    )
    joined["real_pct_change_since_2019"] = joined["real_earnings_index_2019_100"] - 100
    latest = joined.sort_values("year").groupby(keys, as_index=False).tail(1)
    latest = latest.rename(columns={"year": "latest_year"})
    return latest[
        [
            "region",
            "age_group",
            "latest_year",
            "nominal_earnings",
            "real_earnings_index_2019_100",
            "real_pct_change_since_2019",
        ]
    ].sort_values(["region", "age_group"])


def write_policy_brief(summary: pd.DataFrame, latest_year: int) -> None:
    gainers = summary[summary["real_gain_or_loss"].eq("gain")]
    losers = summary[summary["real_gain_or_loss"].eq("loss")]
    weakest = summary.sort_values("real_pct_change").iloc[0]
    strongest = summary.sort_values("real_pct_change").iloc[-1]
    gain_text = ", ".join(gainers["age_group"]) if not gainers.empty else "none"
    loss_text = ", ".join(losers["age_group"]) if not losers.empty else "none"
    lines = [
        "# Policy Brief",
        "",
        "## Headline Answer",
        "",
        (
            f"The age-specific wage comparison currently runs from 2019 to {latest_year}. "
            "It uses ASHE median weekly earnings and deflates them with CPIH."
        ),
        "",
        (
            f"On the baseline run, {weakest['age_group']} is the weakest age-group result: "
            f"{weakest['real_pct_change']:.2f}%. The strongest result is {strongest['age_group']} "
            f"at {strongest['real_pct_change']:.2f}%."
        ),
        (
            "Do not turn the weakest 18-21 result into a simple claim that the youngest "
            "workers clearly became better or worse off. The robustness checks decide how "
            "qualified that wording needs to be."
        ),
        "",
        "## Summary",
        "",
        f"- Real gains in the baseline run: {gain_text}.",
        f"- Real losses in the baseline run: {loss_text}.",
        "- The final summary table also includes `real_pct_change_cpi_deflator`.",
        "",
        "## V2 Triangulation",
        "",
        "- RTI adds monthly age-specific PAYE pay, but it is not an ASHE replacement.",
        "- ASHE hourly pay and hours split weekly earnings into hourly pay, hours, and a residual.",
        "- Minimum wage rates add wage-floor context, not proof that policy caused ASHE changes.",
        "- A05 adds youth labour-market stress context.",
        "- EARN01 adds a current whole-economy wage trend, not age-specific evidence.",
        "",
        "## Limits",
        "",
        "- ASHE is annual and age-specific.",
        "- RTI is monthly PAYE evidence and excludes self-employment income.",
        "- RTI 18-24 does not exactly match ASHE 18-21 or 22-29.",
        "- EARN01 is monthly but not age-specific.",
        "- A05 SA is rolling three-month labour-market data.",
        "- ONS labels A05 SA as official statistics in development.",
        "- This is descriptive analysis, not a causal design.",
    ]
    path = project_path("reports", "policy_brief.md")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create real earnings analysis outputs.")
    parser.parse_args(argv)
    config = load_yaml(ANALYSIS_CONFIG)
    inflation = pd.read_parquet(PROCESSED_ROOT / "inflation_annual.parquet")

    ashe = _filter_main_ashe(pd.read_parquet(PROCESSED_ROOT / "ashe_age_annual.parquet"), config)
    real_age = compute_real_earnings_by_age(ashe, inflation, baseline_year=config["baseline_year"])
    summary = summarise_age_changes(real_age, baseline_year=config["baseline_year"])
    write_dataframe(real_age, PROCESSED_ROOT / "age_group_real_earnings.parquet")
    write_dataframe(summary, OUTPUT_TABLES / "age_group_real_earnings_change.csv")
    write_dataframe(summary, OUTPUT_TABLES / "final_age_group_summary.csv")

    region_source = pd.read_parquet(PROCESSED_ROOT / "ashe_region_age_annual.parquet")
    region_source = region_source[
        region_source["earnings_measure"].eq(config["ashe"]["preferred_measure"])
        & region_source["sex"].eq(config["ashe"]["default_sex"])
        & region_source["work_status"].eq(config["ashe"]["default_work_status"])
    ]
    region_changes = compute_region_age_changes(
        region_source, inflation, baseline_year=config["baseline_year"]
    )
    write_dataframe(region_changes, OUTPUT_TABLES / "region_age_real_earnings_change.csv")
    write_policy_brief(summary, int(real_age["year"].max()))
    print(OUTPUT_TABLES / "age_group_real_earnings_change.csv")
    print(OUTPUT_TABLES / "region_age_real_earnings_change.csv")


if __name__ == "__main__":
    main()
