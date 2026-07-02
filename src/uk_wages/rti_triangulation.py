from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .utils import ensure_dir, load_yaml, project_path


OUTPUT_ROOT = project_path("outputs")
MAPPING_CONFIG = project_path("config", "age_group_mapping.yaml")
RTI_CAVEAT = (
    "RTI is PAYE administrative data. It covers payrolled employees, not "
    "self-employment or all income. Latest flash months are revision-prone. "
    "It measures monthly pay, not ASHE weekly or hourly earnings."
)


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
