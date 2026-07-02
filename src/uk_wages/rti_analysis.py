from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, project_path, write_dataframe


PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_TABLES = project_path("outputs", "tables")
OUTPUT_CHARTS = project_path("outputs", "charts")


def _rebase(df: pd.DataFrame, value_column: str, baseline: pd.Timestamp) -> pd.Series:
    bases = (
        df.loc[df["date"].eq(baseline), ["age_group", value_column]]
        .dropna()
        .set_index("age_group")[value_column]
        .to_dict()
    )
    return df.apply(lambda row: row[value_column] / bases[row["age_group"]] * 100, axis=1)


def compute_rti_real_pay(
    rti: pd.DataFrame,
    inflation_monthly: pd.DataFrame,
    *,
    baseline: pd.Timestamp = pd.Timestamp("2019-01-01"),
) -> pd.DataFrame:
    price = inflation_monthly[["date", "cpih_index_jan2019_100"]]
    joined = rti.merge(price, on="date", how="inner")
    baseline_age_groups = set(joined.loc[joined["date"].eq(baseline), "age_group"])
    joined = joined[joined["age_group"].isin(baseline_age_groups)].copy()
    joined["nominal_pay_index_jan2019_100"] = _rebase(
        joined, "median_monthly_pay", baseline
    )
    joined["real_pay_index_jan2019_100"] = (
        joined["nominal_pay_index_jan2019_100"] / joined["cpih_index_jan2019_100"] * 100
    )
    joined["payrolled_employees_index_jan2019_100"] = _rebase(
        joined, "payrolled_employees", baseline
    )
    joined["nominal_pay_pct_change_since_jan2019"] = (
        joined["nominal_pay_index_jan2019_100"] - 100
    )
    joined["real_pay_pct_change_since_jan2019"] = joined["real_pay_index_jan2019_100"] - 100
    joined["employee_count_pct_change_since_jan2019"] = (
        joined["payrolled_employees_index_jan2019_100"] - 100
    )
    return joined.sort_values(["age_group", "date"]).reset_index(drop=True)


def summarise_rti_changes(real_rti: pd.DataFrame) -> pd.DataFrame:
    latest_non_flash = real_rti[~real_rti["flash_or_provisional_flag"].astype(bool)]
    latest_non_flash_date = (
        pd.Timestamp(latest_non_flash["date"].max()) if not latest_non_flash.empty else pd.NaT
    )
    rows: list[dict[str, object]] = []
    for age_group, group in real_rti.groupby("age_group"):
        ordered = group.sort_values("date")
        latest = ordered.iloc[-1]
        rows.append(
            {
                "age_group": age_group,
                "latest_available_month": pd.Timestamp(latest["date"]).date().isoformat(),
                "latest_available_is_flash_or_provisional": bool(
                    latest["flash_or_provisional_flag"]
                ),
                "latest_non_flash_month": (
                    latest_non_flash_date.date().isoformat()
                    if not pd.isna(latest_non_flash_date)
                    else ""
                ),
                "median_monthly_pay_latest": round(float(latest["median_monthly_pay"]), 2),
                "real_pay_index_jan2019_100": round(
                    float(latest["real_pay_index_jan2019_100"]), 2
                ),
                "real_pay_pct_change_since_jan2019": round(
                    float(latest["real_pay_pct_change_since_jan2019"]), 2
                ),
                "payrolled_employees_index_jan2019_100": round(
                    float(latest["payrolled_employees_index_jan2019_100"]), 2
                ),
                "employee_count_pct_change_since_jan2019": round(
                    float(latest["employee_count_pct_change_since_jan2019"]), 2
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("age_group").reset_index(drop=True)


def _plt():
    import matplotlib.pyplot as plt

    return plt


def _save(fig, name: str) -> None:
    ensure_dir(OUTPUT_CHARTS)
    fig.savefig(OUTPUT_CHARTS / f"{name}.png", dpi=180, bbox_inches="tight")
    fig.savefig(OUTPUT_CHARTS / f"{name}.svg", dpi=180, bbox_inches="tight")
    _plt().close(fig)


def _date_range(data: pd.DataFrame) -> str:
    return (
        f"{pd.Timestamp(data['date'].min()):%b %Y}-"
        f"{pd.Timestamp(data['date'].max()):%b %Y}"
    )


def chart_rti_real_pay(real_rti: pd.DataFrame) -> None:
    plt = _plt()
    focus = real_rti[real_rti["age_group"].isin(["Under 18", "18-24", "25-34", "35-49"])]
    fig, ax = plt.subplots(figsize=(9, 5))
    for age_group, group in focus.groupby("age_group"):
        ax.plot(group["date"], group["real_pay_index_jan2019_100"], label=age_group)
    ax.axhline(100, color="#333333", linewidth=0.8)
    ax.set_title("RTI Real Median Monthly PAYE Pay by Age")
    ax.set_ylabel("Real monthly pay index, Jan 2019 = 100")
    ax.set_xlabel("Month")
    ax.legend(title="RTI age group", ncols=2, fontsize=8)
    ax.grid(alpha=0.25)
    fig.text(
        0.01,
        0.01,
        f"Source: ONS/HMRC PAYE RTI and MM23. Date range: {_date_range(focus)}. "
        "PAYE only; monthly pay, not ASHE weekly or hourly earnings.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    _save(fig, "rti_real_median_monthly_pay_by_age")


def chart_rti_employees(real_rti: pd.DataFrame) -> None:
    plt = _plt()
    focus = real_rti[real_rti["age_group"].isin(["Under 18", "18-24", "25-34", "35-49"])]
    fig, ax = plt.subplots(figsize=(9, 5))
    for age_group, group in focus.groupby("age_group"):
        ax.plot(group["date"], group["payrolled_employees_index_jan2019_100"], label=age_group)
    ax.axhline(100, color="#333333", linewidth=0.8)
    ax.set_title("RTI Payrolled Employees by Age")
    ax.set_ylabel("Payrolled employees index, Jan 2019 = 100")
    ax.set_xlabel("Month")
    ax.legend(title="RTI age group", ncols=2, fontsize=8)
    ax.grid(alpha=0.25)
    fig.text(
        0.01,
        0.01,
        f"Source: ONS/HMRC PAYE RTI. Date range: {_date_range(focus)}. "
        "PAYE employees only; latest month is treated as revision-prone.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    _save(fig, "rti_payrolled_employees_by_age")


def build_rti_outputs(
    *,
    processed_root: str | Path = PROCESSED_ROOT,
    output_tables: str | Path = OUTPUT_TABLES,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    processed_root = Path(processed_root)
    output_tables = ensure_dir(output_tables)
    rti = pd.read_parquet(processed_root / "rti_age_monthly.parquet")
    inflation = pd.read_parquet(processed_root / "inflation_monthly.parquet")
    real_rti = compute_rti_real_pay(rti, inflation)
    summary = summarise_rti_changes(real_rti)
    write_dataframe(real_rti, processed_root / "rti_age_real_monthly.parquet")
    write_dataframe(summary, output_tables / "rti_age_real_pay_change.csv")
    chart_rti_real_pay(real_rti)
    chart_rti_employees(real_rti)
    return real_rti, summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build PAYE RTI real-pay outputs.")
    parser.parse_args(argv)
    _, summary = build_rti_outputs()
    print(OUTPUT_TABLES / "rti_age_real_pay_change.csv")
    print(f"RTI age groups: {', '.join(summary['age_group'].astype(str))}")


if __name__ == "__main__":
    main()
