from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, project_path, write_dataframe


PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_ROOT = project_path("outputs")


def _direction_match(left: object, right: object) -> object:
    if pd.isna(left) or pd.isna(right):
        return pd.NA
    left_sign = 0 if float(left) == 0 else 1 if float(left) > 0 else -1
    right_sign = 0 if float(right) == 0 else 1 if float(right) > 0 else -1
    return left_sign == right_sign


def _corr_or_na(frame: pd.DataFrame, left: str, right: str) -> float | pd.NA:
    values = frame[[left, right]].dropna()
    if len(values) < 2 or values[left].nunique() < 2 or values[right].nunique() < 2:
        return pd.NA
    return round(float(values[left].corr(values[right])), 4)


def _format_concordance(value: object) -> str:
    if pd.isna(value):
        return "not available"
    return f"{float(value):.0%}"


def build_triangulation_metrics(ashe: pd.DataFrame, awe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "real_earnings_index_2019_100" not in ashe.columns:
        empty = pd.DataFrame()
        return empty, empty
    ashe_age = ashe[
        ["year", "age_group", "real_earnings_index_2019_100"]
    ].dropna(subset=["year", "age_group", "real_earnings_index_2019_100"])
    awe_annual = (
        awe[awe["sector"].eq("Whole Economy")]
        .assign(year=lambda df: df["date"].dt.year)
        .groupby("year", as_index=False)[
            ["real_regular_pay_index_jan2019_100", "real_total_pay_index_jan2019_100"]
        ]
        .mean()
    )
    joined = ashe_age.merge(awe_annual, on="year", how="inner").sort_values(
        ["age_group", "year"]
    )
    if joined.empty:
        return joined, pd.DataFrame()
    joined["ashe_yoy_change"] = joined.groupby("age_group")[
        "real_earnings_index_2019_100"
    ].diff()
    joined["earn01_regular_yoy_change"] = joined.groupby("age_group")[
        "real_regular_pay_index_jan2019_100"
    ].diff()
    joined["earn01_total_yoy_change"] = joined.groupby("age_group")[
        "real_total_pay_index_jan2019_100"
    ].diff()
    previous_year = joined.groupby("age_group")["year"].shift()
    adjacent_year = joined["year"].sub(previous_year).eq(1)
    joined.loc[
        ~adjacent_year,
        ["ashe_yoy_change", "earn01_regular_yoy_change", "earn01_total_yoy_change"],
    ] = pd.NA
    joined["regular_direction_match"] = [
        _direction_match(left, right)
        for left, right in zip(joined["ashe_yoy_change"], joined["earn01_regular_yoy_change"])
    ]
    joined["total_direction_match"] = [
        _direction_match(left, right)
        for left, right in zip(joined["ashe_yoy_change"], joined["earn01_total_yoy_change"])
    ]
    joined["regular_level_gap_pp"] = (
        joined["real_earnings_index_2019_100"] - joined["real_regular_pay_index_jan2019_100"]
    )
    joined["total_level_gap_pp"] = (
        joined["real_earnings_index_2019_100"] - joined["real_total_pay_index_jan2019_100"]
    )

    rows: list[dict[str, object]] = []
    for age_group, group in joined.groupby("age_group"):
        comparable = group.dropna(subset=["ashe_yoy_change"])
        latest = group.sort_values("year").iloc[-1]
        rows.append(
            {
                "age_group": age_group,
                "overlap_years": int(group["year"].nunique()),
                "yoy_comparison_years": int(len(comparable)),
                "regular_direction_concordance": round(
                    float(comparable["regular_direction_match"].mean()), 4
                )
                if not comparable.empty
                else pd.NA,
                "total_direction_concordance": round(
                    float(comparable["total_direction_match"].mean()), 4
                )
                if not comparable.empty
                else pd.NA,
                "regular_yoy_correlation": _corr_or_na(
                    comparable, "ashe_yoy_change", "earn01_regular_yoy_change"
                ),
                "total_yoy_correlation": _corr_or_na(
                    comparable, "ashe_yoy_change", "earn01_total_yoy_change"
                ),
                "latest_year": int(latest["year"]),
                "latest_ashe_index": round(float(latest["real_earnings_index_2019_100"]), 2),
                "latest_earn01_regular_index": round(
                    float(latest["real_regular_pay_index_jan2019_100"]), 2
                ),
                "latest_earn01_total_index": round(
                    float(latest["real_total_pay_index_jan2019_100"]), 2
                ),
                "latest_regular_level_gap_pp": round(float(latest["regular_level_gap_pp"]), 2),
                "latest_total_level_gap_pp": round(float(latest["total_level_gap_pp"]), 2),
            }
        )
    summary = pd.DataFrame(rows).sort_values("age_group").reset_index(drop=True)
    metrics = joined.round(
        {
            "real_earnings_index_2019_100": 4,
            "real_regular_pay_index_jan2019_100": 4,
            "real_total_pay_index_jan2019_100": 4,
            "ashe_yoy_change": 4,
            "earn01_regular_yoy_change": 4,
            "earn01_total_yoy_change": 4,
            "regular_level_gap_pp": 4,
            "total_level_gap_pp": 4,
        }
    )
    return metrics.reset_index(drop=True), summary


def build_triangulation_report(
    *,
    processed_root: str | Path = PROCESSED_ROOT,
    output_root: str | Path = OUTPUT_ROOT,
) -> Path:
    processed_root = Path(processed_root)
    output_root = Path(output_root)
    evidence_root = ensure_dir(output_root / "evidence")
    ashe = pd.read_parquet(processed_root / "age_group_real_earnings.parquet")
    awe = pd.read_parquet(processed_root / "awe_real_monthly.parquet")
    metrics, summary = build_triangulation_metrics(ashe, awe)
    if not metrics.empty:
        write_dataframe(metrics, evidence_root / "triangulation_metrics.csv")
    if not summary.empty:
        write_dataframe(summary, evidence_root / "triangulation_summary.csv")
    lines = [
        "# Triangulation Report",
        "",
        "ASHE and EARN01 measure different things, so exact agreement is not expected.",
        "EARN01 is not age-specific; it is a whole-economy and sector wage source.",
        "",
    ]
    if summary.empty:
        lines.append("No overlapping ASHE/EARN01 annual comparison could be built.")
    else:
        latest_year = int(summary["latest_year"].max())
        lines.extend(
            [
                f"Latest overlapping year: {latest_year}.",
                "",
                "## Age-Specific Comparison",
                "",
            ]
        )
        for row in summary.itertuples(index=False):
            lines.append(
                f"- ASHE {row.age_group}: latest ASHE index {row.latest_ashe_index:.2f}; "
                f"EARN01 regular-pay index {row.latest_earn01_regular_index:.2f}; "
                f"latest regular-pay gap {row.latest_regular_level_gap_pp:.2f} percentage points. "
                f"Directional concordance with EARN01 regular pay is "
                f"{_format_concordance(row.regular_direction_concordance)} across "
                f"{int(row.yoy_comparison_years)} year-over-year comparisons."
            )
        lines.extend(
            [
                "",
                "Interpretation:",
                "Use direction and magnitude gaps as evidence that dataset frequency, population, sector mix, and bonuses matter. EARN01 is a comparator for whole-economy wage pressure, not an age-specific replacement for ASHE.",
            ]
        )
    path = evidence_root / "triangulation_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare ASHE and EARN01 real-pay signals.")
    parser.parse_args(argv)
    print(build_triangulation_report())


if __name__ == "__main__":
    main()
