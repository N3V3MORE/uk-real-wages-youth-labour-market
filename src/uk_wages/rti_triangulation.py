from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, load_yaml, project_path, write_dataframe


OUTPUT_ROOT = project_path("outputs")
PROCESSED_ROOT = project_path("data", "processed")
MAPPING_CONFIG = project_path("config", "age_group_mapping.yaml")
RTI_CAVEAT = (
    "RTI is PAYE administrative data. It covers payrolled employees, not "
    "self-employment or all income. Latest flash months are revision-prone. "
    "It measures monthly pay, not ASHE weekly or hourly earnings."
)


def _direction_match(left: float, right: float) -> bool:
    left_sign = 0 if float(left) == 0 else 1 if float(left) > 0 else -1
    right_sign = 0 if float(right) == 0 else 1 if float(right) > 0 else -1
    return left_sign == right_sign


def _default_processed_root(output_root: Path) -> Path:
    colocated = output_root.parent / "data" / "processed"
    return colocated if colocated.exists() else PROCESSED_ROOT


def build_annual_rti_ashe_comparison(
    *,
    output_root: str | Path = OUTPUT_ROOT,
    mapping_config: str | Path = MAPPING_CONFIG,
    processed_root: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    output_root = Path(output_root)
    processed = (
        Path(processed_root) if processed_root is not None else _default_processed_root(output_root)
    )
    rti_path = processed / "rti_age_real_monthly.parquet"
    ashe_path = processed / "age_group_real_earnings.parquet"
    columns = [
        "year",
        "comparison_month",
        "rti_age_group",
        "ashe_age_group",
        "ashe_real_earnings_index_2019_100",
        "rti_real_pay_index_april2019_100",
        "ashe_yoy_change",
        "rti_yoy_change",
        "direction_match",
        "level_gap_pp",
    ]
    if not rti_path.exists() or not ashe_path.exists():
        return pd.DataFrame(columns=columns), pd.DataFrame()

    mapping = load_yaml(mapping_config)["rti_to_ashe_comparison"]
    rti = pd.read_parquet(rti_path).copy()
    ashe = pd.read_parquet(ashe_path).copy()
    rti["date"] = pd.to_datetime(rti["date"])
    rti_april = rti[rti["date"].dt.month.eq(4)].copy()
    if rti_april.empty or ashe.empty:
        return pd.DataFrame(columns=columns), pd.DataFrame()
    rti_april["year"] = rti_april["date"].dt.year
    baseline = (
        rti_april[rti_april["year"].eq(2019)]
        .set_index("age_group")["real_pay_index_jan2019_100"]
        .to_dict()
    )
    rti_april = rti_april[rti_april["age_group"].isin(baseline)].copy()
    rti_april["rti_real_pay_index_april2019_100"] = rti_april.apply(
        lambda row: row["real_pay_index_jan2019_100"] / baseline[row["age_group"]] * 100,
        axis=1,
    )

    rows: list[dict[str, object]] = []
    for bridge in mapping:
        rti_age_group = str(bridge["rti_age_group"])
        closest = bridge.get("closest_ashe_groups") or []
        if not closest:
            continue
        rti_group = rti_april[rti_april["age_group"].eq(rti_age_group)][
            ["year", "rti_real_pay_index_april2019_100"]
        ].sort_values("year")
        rti_group["rti_yoy_change"] = rti_group["rti_real_pay_index_april2019_100"].diff()
        rti_adjacent_year = rti_group["year"].sub(rti_group["year"].shift()).eq(1)
        rti_group.loc[~rti_adjacent_year, "rti_yoy_change"] = pd.NA
        for ashe_age_group in closest:
            ashe_group = ashe[ashe["age_group"].eq(ashe_age_group)][
                ["year", "real_earnings_index_2019_100"]
            ].sort_values("year")
            ashe_group["ashe_yoy_change"] = ashe_group[
                "real_earnings_index_2019_100"
            ].diff()
            ashe_adjacent_year = ashe_group["year"].sub(ashe_group["year"].shift()).eq(1)
            ashe_group.loc[~ashe_adjacent_year, "ashe_yoy_change"] = pd.NA
            joined = ashe_group.merge(rti_group, on="year", how="inner").dropna(
                subset=["ashe_yoy_change", "rti_yoy_change"]
            )
            for row in joined.itertuples(index=False):
                rows.append(
                    {
                        "year": int(row.year),
                        "comparison_month": "April",
                        "rti_age_group": rti_age_group,
                        "ashe_age_group": ashe_age_group,
                        "ashe_real_earnings_index_2019_100": round(
                            float(row.real_earnings_index_2019_100), 4
                        ),
                        "rti_real_pay_index_april2019_100": round(
                            float(row.rti_real_pay_index_april2019_100), 4
                        ),
                        "ashe_yoy_change": round(float(row.ashe_yoy_change), 4),
                        "rti_yoy_change": round(float(row.rti_yoy_change), 4),
                        "direction_match": _direction_match(
                            row.ashe_yoy_change, row.rti_yoy_change
                        ),
                        "level_gap_pp": round(
                            float(
                                row.real_earnings_index_2019_100
                                - row.rti_real_pay_index_april2019_100
                            ),
                            4,
                        ),
                    }
                )
    comparison = pd.DataFrame(rows, columns=columns)
    if comparison.empty:
        return comparison, pd.DataFrame()
    summary_rows: list[dict[str, object]] = []
    for (summary_rti_age_group, summary_ashe_age_group), group in comparison.groupby(
        ["rti_age_group", "ashe_age_group"]
    ):
        latest = group.sort_values("year").iloc[-1]
        summary_rows.append(
            {
                "rti_age_group": summary_rti_age_group,
                "ashe_age_group": summary_ashe_age_group,
                "overlap_start_year": int(group["year"].min()),
                "overlap_end_year": int(group["year"].max()),
                "comparison_years": int(len(group)),
                "directional_concordance": round(float(group["direction_match"].mean()), 4),
                "latest_level_gap_pp": round(float(latest["level_gap_pp"]), 2),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values(
        ["rti_age_group", "ashe_age_group"]
    ).reset_index(drop=True)
    return comparison.reset_index(drop=True), summary


def build_rti_triangulation_report(
    *,
    output_root: str | Path = OUTPUT_ROOT,
    mapping_config: str | Path = MAPPING_CONFIG,
) -> Path:
    output_root = Path(output_root)
    tables = output_root / "tables"
    evidence = ensure_dir(output_root / "evidence")
    rti = pd.read_csv(tables / "rti_age_real_pay_change.csv")
    ashe = pd.read_csv(tables / "age_group_real_earnings_change.csv")
    mapping = load_yaml(mapping_config)["rti_to_ashe_comparison"]
    annual_comparison, annual_summary = build_annual_rti_ashe_comparison(
        output_root=output_root,
        mapping_config=mapping_config,
    )
    if not annual_comparison.empty:
        write_dataframe(annual_comparison, evidence / "rti_ashe_annual_comparison.csv")
    if not annual_summary.empty:
        write_dataframe(annual_summary, evidence / "rti_ashe_annual_summary.csv")

    rti_18_24 = rti[rti["age_group"].eq("18-24")].iloc[0]
    ashe_focus = ashe[ashe["age_group"].isin(["18-21", "22-29"])].copy()
    latest_month = str(rti_18_24["latest_available_month"])
    latest_year = int(ashe_focus["latest_year"].max())
    lines = [
        "# RTI and ASHE Triangulation",
        "",
        "RTI is a monthly PAYE check on the ASHE story. It does not replace ASHE.",
        "",
        "## Source Boundary",
        "",
        RTI_CAVEAT,
        "",
        "ASHE remains the main annual age-specific earnings source. The latest ASHE age-specific wage year in this pipeline is "
        f"{latest_year}; RTI extends the monthly PAYE view to {latest_month}.",
        "",
        "## Age-Band Bridge",
        "",
    ]
    for row in mapping:
        closest = row.get("closest_ashe_groups") or []
        ashe_label = ", ".join(closest) if closest else "no exact ASHE match"
        lines.append(
            f"- RTI {row['rti_age_group']} -> ASHE {ashe_label}: "
            f"{row['comparison_quality']}. {row['note']}"
        )
    lines.extend(
        [
            "",
            "## Read Across",
            "",
            (
                f"RTI 18-24 real median monthly PAYE pay is "
                f"{float(rti_18_24['real_pay_pct_change_since_jan2019']):.2f}% from January 2019 "
                f"to {latest_month}."
            ),
        ]
    )
    for row in ashe_focus.sort_values("age_group").itertuples(index=False):
        lines.append(
            f"- ASHE {row.age_group} real median weekly earnings: "
            f"{float(row.real_pct_change):.2f}% from 2019 to {int(row.latest_year)}."
        )
    lines.extend(
        [
            "",
            "## April-to-April overlap",
            "",
        ]
    )
    if annual_summary.empty:
        lines.append(
            "No April-to-April overlap table could be built from processed monthly RTI and annual ASHE series."
        )
    else:
        for row in annual_summary.itertuples(index=False):
            lines.append(
                f"- RTI {row.rti_age_group} versus ASHE {row.ashe_age_group}: "
                f"Directional concordance is {float(row.directional_concordance):.0%} "
                f"across {int(row.comparison_years)} April-to-April year-over-year comparisons "
                f"({int(row.overlap_start_year)}-{int(row.overlap_end_year)}); "
                f"latest level gap is {float(row.latest_level_gap_pp):.2f} percentage points."
            )
    lines.extend(
        [
            "",
            "The clean conclusion is not that one source wins. ASHE measures annual weekly earnings by ASHE age band; RTI measures monthly PAYE pay by RTI age band. If RTI 18-24 and ASHE 18-21 point in different directions, the right wording is that the youngest-worker story is harder to summarise, not that the ASHE result has been disproved.",
            "",
        ]
    )
    path = evidence / "rti_ashe_triangulation.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare RTI age pay with ASHE age pay.")
    parser.parse_args(argv)
    print(build_rti_triangulation_report())


if __name__ == "__main__":
    main()
