from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, project_path


PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_CHARTS = project_path("outputs", "charts")
OUTPUT_TABLES = project_path("outputs", "tables")
def _plt():
    import matplotlib.pyplot as plt

    return plt


def _save(fig, name: str) -> None:
    ensure_dir(OUTPUT_CHARTS)
    for suffix in [".png", ".svg"]:
        fig.savefig(OUTPUT_CHARTS / f"{name}{suffix}", dpi=180, bbox_inches="tight")
    _plt().close(fig)


def _add_note(fig, note: str) -> None:
    fig.text(0.01, 0.01, note, ha="left", va="bottom", fontsize=8, color="#555555")


def _year_range(data: pd.DataFrame, column: str = "year") -> str:
    return f"{int(data[column].min())}-{int(data[column].max())}"


def _date_range(data: pd.DataFrame, column: str = "date") -> str:
    start = pd.Timestamp(data[column].min()).strftime("%b %Y")
    end = pd.Timestamp(data[column].max()).strftime("%b %Y")
    return f"{start}-{end}"


def chart_real_earnings_by_age() -> None:
    plt = _plt()
    data = pd.read_parquet(PROCESSED_ROOT / "age_group_real_earnings.parquet")
    fig, ax = plt.subplots(figsize=(9, 5))
    for age_group, group in data.groupby("age_group"):
        ax.plot(group["year"], group["real_earnings_index_2019_100"], marker="o", label=age_group)
    ax.axhline(100, color="#555555", linewidth=0.8)
    ax.set_title("Real Earnings by Age Group, 2019 to Latest ASHE Year")
    ax.set_ylabel("Real earnings index, 2019 = 100")
    ax.set_xlabel("ASHE year")
    ax.legend(title="Age group", ncols=2, fontsize=8)
    ax.grid(alpha=0.25)
    _add_note(
        fig,
        f"Source: ONS ASHE Table 6 and MM23. Date range: {_year_range(data)}. "
        "Units: real earnings index, 2019 = 100. Deflator: CPIH all-items, April index.",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    _save(fig, "real_earnings_by_age")


def chart_real_earnings_change_by_age() -> None:
    plt = _plt()
    data = pd.read_csv(OUTPUT_TABLES / "age_group_real_earnings_change.csv")
    data = data.sort_values("real_pct_change")
    colors = ["#b44b4b" if value < 0 else "#3d7f5b" for value in data["real_pct_change"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(data["age_group"], data["real_pct_change"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_title("Real Earnings Change Since 2019 by Age Group")
    ax.set_xlabel("Real percent change")
    ax.set_ylabel("Age group")
    ax.grid(axis="x", alpha=0.25)
    _add_note(
        fig,
        f"Source: ONS ASHE Table 6 and MM23. Date range: 2019-{int(data['latest_year'].max())}. "
        "Units: real percent change. Deflator: CPIH all-items, April index.",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    _save(fig, "real_earnings_change_by_age")


def chart_region_age() -> None:
    plt = _plt()
    data = pd.read_csv(OUTPUT_TABLES / "region_age_real_earnings_change.csv")
    data = data[data["age_group"].isin(["18-21", "22-29", "30-39"])]
    pivot = data.pivot_table(
        index="region", columns="age_group", values="real_pct_change_since_2019", aggfunc="first"
    ).sort_index()
    fig, ax = plt.subplots(figsize=(9, 6))
    image = ax.imshow(pivot, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)), pivot.columns)
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    ax.set_title("Young Worker Real Earnings Change by UK Region")
    ax.set_xlabel("Age group")
    ax.set_ylabel("Region")
    for y, region in enumerate(pivot.index):
        for x, age in enumerate(pivot.columns):
            value = pivot.loc[region, age]
            if pd.notna(value):
                ax.text(x, y, f"{value:.1f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, label="Real percent change since 2019")
    _add_note(
        fig,
        f"Source: ONS ASHE UK region by age group and MM23. Date range: 2019-{int(data['latest_year'].max())}. "
        "Units: real percent change. Deflator: CPIH all-items, April index.",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    _save(fig, "young_worker_real_earnings_by_region")


def chart_youth_stress() -> None:
    plt = _plt()
    data = pd.read_parquet(PROCESSED_ROOT / "a05_age_labour_market.parquet")
    youth = data[data["age_group"].eq("16-24")]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(youth["date"], youth["unemployment_rate"], label="Unemployment rate", color="#b44b4b")
    ax.plot(youth["date"], youth["inactivity_rate"], label="Inactivity rate", color="#4b6fb4")
    ax.set_title("Youth Unemployment and Inactivity Rates")
    ax.set_ylabel("Rate (%)")
    ax.set_xlabel("Rolling three-month period end")
    ax.legend()
    ax.grid(alpha=0.25)
    _add_note(
        fig,
        f"Source: ONS A05 SA. Date range: {_date_range(youth)}. Units: rate (%). "
        "Rates are seasonally adjusted rolling three-month estimates. A05 SA is official statistics in development.",
    )
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    _save(fig, "youth_labour_market_stress")


def chart_wage_growth_minus_inflation() -> None:
    plt = _plt()
    data = pd.read_parquet(PROCESSED_ROOT / "age_group_real_earnings.parquet")
    fig, ax = plt.subplots(figsize=(9, 5))
    for age_group, group in data.groupby("age_group"):
        ax.plot(group["year"], group["real_pct_change_since_2019"], marker="o", label=age_group)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("Wage Growth Minus Inflation, ASHE Annual Version")
    ax.set_ylabel("Real percent change since 2019")
    ax.set_xlabel("ASHE year")
    ax.legend(title="Age group", ncols=2, fontsize=8)
    ax.grid(alpha=0.25)
    _add_note(
        fig,
        f"Source: ONS ASHE Table 6 and MM23. Date range: {_year_range(data)}. "
        "Units: real percent change since 2019. Deflator: CPIH all-items, April index.",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    _save(fig, "wage_growth_minus_inflation_ashe")


def chart_monthly_awe() -> None:
    plt = _plt()
    data = pd.read_parquet(PROCESSED_ROOT / "awe_real_monthly.parquet")
    whole = data[data["sector"].eq("Whole Economy")]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(whole["date"], whole["real_regular_pay_index_jan2019_100"], label="Regular pay")
    ax.plot(whole["date"], whole["real_total_pay_index_jan2019_100"], label="Total pay")
    ax.axhline(100, color="#333333", linewidth=0.8)
    ax.set_title("Monthly Real Regular Pay and Total Pay")
    ax.set_ylabel("Real pay index, Jan 2019 = 100")
    ax.set_xlabel("Month")
    ax.legend()
    ax.grid(alpha=0.25)
    _add_note(
        fig,
        f"Source: ONS EARN01 and MM23. Date range: {_date_range(whole)}. "
        "Units: real pay index, Jan 2019 = 100. Deflator: CPIH all-items monthly index. "
        "EARN01 is monthly but not age-specific.",
    )
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    _save(fig, "monthly_real_awe")


def build_all_charts() -> None:
    chart_real_earnings_by_age()
    chart_real_earnings_change_by_age()
    chart_region_age()
    chart_youth_stress()
    chart_wage_growth_minus_inflation()
    chart_monthly_awe()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create publication charts.")
    parser.parse_args(argv)
    build_all_charts()
    print(OUTPUT_CHARTS)


if __name__ == "__main__":
    main()
