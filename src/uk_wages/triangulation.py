from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, project_path


PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_ROOT = project_path("outputs")


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
    ashe_all = (
        ashe.groupby("year", as_index=False)["real_earnings_index_2019_100"].mean()
        if "real_earnings_index_2019_100" in ashe.columns
        else pd.DataFrame()
    )
    awe_annual = (
        awe[awe["sector"].eq("Whole Economy")]
        .assign(year=lambda df: df["date"].dt.year)
        .groupby("year", as_index=False)[
            ["real_regular_pay_index_jan2019_100", "real_total_pay_index_jan2019_100"]
        ]
        .mean()
    )
    joined = ashe_all.merge(awe_annual, on="year", how="inner")
    lines = [
        "# Triangulation Report",
        "",
        "ASHE and EARN01 measure different things, so exact agreement is not expected.",
        "EARN01 is not age-specific; it is a whole-economy and sector wage source.",
        "",
    ]
    if joined.empty:
        lines.append("No overlapping ASHE/EARN01 annual comparison could be built.")
    else:
        latest = joined.sort_values("year").iloc[-1]
        lines.extend(
            [
                f"Latest overlapping year: {int(latest['year'])}.",
                f"ASHE age-group average real index: {latest['real_earnings_index_2019_100']:.2f}.",
                f"EARN01 real regular pay annual average index: {latest['real_regular_pay_index_jan2019_100']:.2f}.",
                f"EARN01 real total pay annual average index: {latest['real_total_pay_index_jan2019_100']:.2f}.",
                "",
                "Interpretation:",
                "Use differences as evidence that dataset frequency, population, sector mix, and bonuses matter.",
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
