from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from .utils import clean_numeric_value, project_path, single_matching_file, write_dataframe


RAW_ROOT = project_path("data", "raw", "minimum_wage")
PROCESSED_ROOT = project_path("data", "processed")
OUTPUT_TABLES = project_path("outputs", "tables")
OUTPUT_CHARTS = project_path("outputs", "charts")
EVIDENCE_ROOT = project_path("outputs", "evidence")


def _rate_value(value: str) -> float:
    cleaned = clean_numeric_value(value.replace("£", "").replace("\xa0", " "))
    if pd.isna(cleaned):
        raise ValueError(f"Cannot parse minimum wage rate: {value!r}")
    return float(cleaned)


def _series_for_band(age_band: str) -> str:
    if "and over" in age_band:
        return "adult threshold"
    return age_band


def parse_minimum_wage_html(html: str, *, source_file: str = "minimum_wage.html") -> pd.DataFrame:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, object]] = []
    for table in soup.find_all("table"):
        headers = [cell.get_text(" ", strip=True) for cell in table.find_all("th", scope="col")]
        if not headers:
            continue
        for body_row in table.find_all("tr"):
            label_cell = body_row.find("th", scope="row")
            if label_cell is None:
                continue
            period = label_cell.get_text(" ", strip=True)
            match = re.search(r"April\s+(\d{4})", period)
            if not match:
                continue
            year = int(match.group(1))
            cells = [cell.get_text(" ", strip=True) for cell in body_row.find_all("td")]
            for age_band, value in zip(headers, cells):
                if not value:
                    continue
                rows.append(
                    {
                        "effective_year": year,
                        "effective_date": pd.Timestamp(year=year, month=4, day=1),
                        "period_label": period,
                        "age_band": age_band,
                        "policy_series": _series_for_band(age_band),
                        "nominal_hourly_rate": _rate_value(value),
                        "source_file": source_file,
                        "source_url": "https://www.gov.uk/national-minimum-wage-rates",
                    }
                )
    if not rows:
        raise ValueError("No minimum wage rows were parsed from GOV.UK HTML.")
    result = pd.DataFrame(rows).drop_duplicates(
        ["effective_year", "age_band"], keep="first"
    )
    return result.sort_values(["policy_series", "effective_year", "age_band"]).reset_index(
        drop=True
    )


def read_minimum_wage_html(source: str | Path) -> str:
    source = Path(source)
    if source.suffix.lower() == ".html":
        return source.read_text(encoding="utf-8")
    if source.suffix.lower() != ".json":
        raise ValueError(f"Unsupported GOV.UK minimum wage source format: {source.name}")
    payload = json.loads(source.read_text(encoding="utf-8"))
    details = payload.get("details")
    body = details.get("body") if isinstance(details, dict) else None
    if not isinstance(body, str) or not body.strip():
        raise ValueError(f"GOV.UK minimum wage JSON has no nonempty details.body: {source}")
    return body


def build_minimum_wage_rates(raw_root: str | Path = RAW_ROOT) -> pd.DataFrame:
    source = single_matching_file(raw_root, ["**/minimum_wage.json", "**/minimum_wage.html"])
    return parse_minimum_wage_html(read_minimum_wage_html(source), source_file=source.name)


def compute_real_minimum_wage_rates(
    rates: pd.DataFrame,
    inflation_annual: pd.DataFrame,
) -> pd.DataFrame:
    price = inflation_annual[["year", "cpih_april_index"]].rename(
        columns={"year": "effective_year"}
    )
    joined = rates.merge(price, on="effective_year", how="inner")
    bases = (
        joined[joined["effective_year"].eq(2019)]
        .set_index("policy_series")[["nominal_hourly_rate", "cpih_april_index"]]
        .to_dict("index")
    )
    joined["real_hourly_rate_2019_prices"] = joined.apply(
        lambda row: row["nominal_hourly_rate"]
        / row["cpih_april_index"]
        * bases.get(row["policy_series"], {"cpih_april_index": pd.NA})["cpih_april_index"],
        axis=1,
    )
    joined["real_statutory_wage_index_2019_100"] = joined.apply(
        lambda row: (
            row["real_hourly_rate_2019_prices"]
            / (
                bases[row["policy_series"]]["nominal_hourly_rate"]
                if row["policy_series"] in bases
                else row["real_hourly_rate_2019_prices"]
            )
            * 100
            if row["policy_series"] in bases
            else pd.NA
        ),
        axis=1,
    )
    return joined.sort_values(["policy_series", "effective_year", "age_band"]).reset_index(
        drop=True
    )


def compute_minimum_wage_bite(real_rates: pd.DataFrame, processed_root: str | Path) -> pd.DataFrame:
    processed_root = Path(processed_root)
    decomp_path = processed_root / "ashe_age_hours_decomposition.parquet"
    if not decomp_path.exists():
        return pd.DataFrame(
            [
                {
                    "ashe_age_group": "",
                    "policy_series": "",
                    "calculation_status": "skipped",
                    "note": "ASHE hourly pay decomposition is unavailable.",
                }
            ]
        )
    ashe = pd.read_parquet(decomp_path)
    if "hourly_gross" not in ashe.columns:
        return pd.DataFrame(
            [
                {
                    "ashe_age_group": "",
                    "policy_series": "",
                    "calculation_status": "skipped",
                    "note": "ASHE hourly gross pay was not parsed.",
                }
            ]
        )
    mappings = [
        ("18-21", "18 to 20", "imperfect: ASHE 18-21 includes 21-year-olds"),
        ("22-29", "adult threshold", "imperfect: adult statutory age threshold changes over time"),
    ]
    rows: list[dict[str, object]] = []
    for age_group, policy_series, note in mappings:
        ashe_focus = ashe[ashe["age_group"].eq(age_group)]
        rates_focus = real_rates[real_rates["policy_series"].eq(policy_series)]
        for _, rate_row in rates_focus.iterrows():
            year = int(rate_row["effective_year"])
            ashe_row = ashe_focus[ashe_focus["year"].eq(year)]
            if ashe_row.empty:
                continue
            hourly_pay = float(ashe_row.iloc[0]["hourly_gross"])
            rows.append(
                {
                    "year": year,
                    "ashe_age_group": age_group,
                    "policy_series": policy_series,
                    "statutory_age_band": rate_row["age_band"],
                    "statutory_hourly_rate": round(float(rate_row["nominal_hourly_rate"]), 2),
                    "ashe_median_hourly_pay": round(hourly_pay, 2),
                    "minimum_wage_bite": round(
                        float(rate_row["nominal_hourly_rate"]) / hourly_pay, 4
                    ),
                    "calculation_status": "calculated",
                    "note": note,
                }
            )
    if not rows:
        rows.append(
            {
                "ashe_age_group": "",
                "policy_series": "",
                "calculation_status": "skipped",
                "note": "No overlapping ASHE hourly pay and statutory wage years were available.",
            }
        )
    return pd.DataFrame(rows).sort_values(["ashe_age_group", "year"]).reset_index(drop=True)


def _plt():
    import matplotlib.pyplot as plt

    return plt


def chart_real_rates(real_rates: pd.DataFrame) -> None:
    plt = _plt()
    focus = real_rates[
        real_rates["policy_series"].isin(["adult threshold", "18 to 20", "Under 18"])
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    for series, group in focus.groupby("policy_series"):
        ax.plot(group["effective_year"], group["real_statutory_wage_index_2019_100"], marker="o", label=series)
    ax.axhline(100, color="#333333", linewidth=0.8)
    ax.set_title("Real Statutory Minimum Wage by Age Band")
    ax.set_ylabel("Real statutory wage index, 2019 = 100")
    ax.set_xlabel("April rate year")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.text(
        0.01,
        0.01,
        "Source: GOV.UK minimum wage rates and ONS MM23. Deflator: April CPIH.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    OUTPUT_CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_CHARTS / "real_minimum_wage_by_age.png", dpi=180, bbox_inches="tight")
    fig.savefig(OUTPUT_CHARTS / "real_minimum_wage_by_age.svg", dpi=180, bbox_inches="tight")
    plt.close(fig)


def chart_bite(bite: pd.DataFrame) -> None:
    if bite.empty or not bite["calculation_status"].eq("calculated").any():
        return
    plt = _plt()
    plot = bite[bite["calculation_status"].eq("calculated")]
    fig, ax = plt.subplots(figsize=(8, 5))
    for age_group, group in plot.groupby("ashe_age_group"):
        ax.plot(group["year"], group["minimum_wage_bite"], marker="o", label=age_group)
    ax.set_title("Minimum Wage Bite for Young ASHE Groups")
    ax.set_ylabel("Statutory rate / ASHE median hourly pay")
    ax.set_xlabel("April ASHE year")
    ax.legend(title="ASHE group", fontsize=8)
    ax.grid(alpha=0.25)
    fig.text(
        0.01,
        0.01,
        "Source: GOV.UK minimum wage rates and ONS ASHE Table 6. Age mapping is imperfect.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    OUTPUT_CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        OUTPUT_CHARTS / "minimum_wage_bite_young_workers.png", dpi=180, bbox_inches="tight"
    )
    fig.savefig(
        OUTPUT_CHARTS / "minimum_wage_bite_young_workers.svg", dpi=180, bbox_inches="tight"
    )
    plt.close(fig)


def write_minimum_wage_report(real_rates: pd.DataFrame, bite: pd.DataFrame) -> Path:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    latest = real_rates["effective_year"].max()
    lines = [
        "# Minimum Wage Context",
        "",
        "GOV.UK statutory wage-floor rates are policy context. They do not prove that minimum wage changes caused ASHE wage changes.",
        "",
        "## What The Source Can Prove",
        "",
        "It can show the nominal and CPIH-deflated statutory hourly wage floor by age threshold. It cannot show actual hourly pay for all young workers, hours worked, or composition effects.",
        "",
        "## Current Coverage",
        "",
        f"Rates from April 2019 through April {latest} are parsed from GOV.UK.",
        "Since April 2024 the National Living Wage threshold has been 21 and over; before that the adult threshold was older.",
        "",
        "## Bite Calculation",
        "",
    ]
    if bite.empty or not bite["calculation_status"].eq("calculated").any():
        note = bite.iloc[0]["note"] if not bite.empty and "note" in bite.columns else "Bite was not calculated."
        lines.append(str(note))
    else:
        calculated = bite[bite["calculation_status"].eq("calculated")]
        for row in calculated.sort_values(["ashe_age_group", "year"]).itertuples(index=False):
            lines.append(
                f"- {row.year} {row.ashe_age_group}: statutory {row.policy_series} rate was "
                f"{row.minimum_wage_bite:.2f} of ASHE median hourly pay ({row.note})."
            )
    lines.extend(
        [
            "",
            "Use this section as context only. ASHE age bands do not line up exactly with statutory age thresholds.",
            "",
        ]
    )
    path = EVIDENCE_ROOT / "minimum_wage_context.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_minimum_wage_outputs(
    *,
    raw_root: str | Path = RAW_ROOT,
    processed_root: str | Path = PROCESSED_ROOT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rates = build_minimum_wage_rates(raw_root)
    inflation = pd.read_parquet(Path(processed_root) / "inflation_annual.parquet")
    real_rates = compute_real_minimum_wage_rates(rates, inflation)
    bite = compute_minimum_wage_bite(real_rates, processed_root)
    write_dataframe(rates, Path(processed_root) / "minimum_wage_rates.parquet")
    write_dataframe(real_rates, OUTPUT_TABLES / "minimum_wage_real_rates.csv")
    write_dataframe(bite, OUTPUT_TABLES / "minimum_wage_bite_by_age.csv")
    chart_real_rates(real_rates)
    chart_bite(bite)
    write_minimum_wage_report(real_rates, bite)
    return real_rates, bite


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build minimum wage context outputs.")
    parser.parse_args(argv)
    build_minimum_wage_outputs()
    print(OUTPUT_TABLES / "minimum_wage_real_rates.csv")


if __name__ == "__main__":
    main()
