from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from uk_wages.ashe_decomposition import (
    compute_decomposition,
    inspect_ashe_decomposition_availability,
    write_decomposition_report,
)
from uk_wages.claims import assess_claims
from uk_wages.clean_rti import parse_rti_age_workbook
from uk_wages.minimum_wage import (
    compute_minimum_wage_bite,
    compute_real_minimum_wage_rates,
    parse_minimum_wage_html,
)
from uk_wages import minimum_wage
from uk_wages import source_validation
from uk_wages.rti_analysis import compute_rti_real_pay
from uk_wages.rti_triangulation import build_rti_triangulation_report
from uk_wages.research_note import build_research_note
from uk_wages.source_validation import REQUIRED_SOURCE_CHECKS
from uk_wages.source_validation import (
    _raw_minimum_wage_rate_cell,
    _raw_rti_median_pay_cell,
)


def _write_rti_workbook(path: Path) -> None:
    index = pd.DataFrame(
        [
            ["Earnings and employment from Pay As You Earn Real Time Information, UK"],
            ["Date of publication: 18 June 2026"],
            ["Figures for May 2026 are early estimates."],
        ]
    )
    header = ["Date", "0 to 17", "18 to 24", "25 to 34", "35 to 49", "50 to 64", "65 and over", "UK"]
    employees = pd.DataFrame(
        [
            ["28. Payrolled employees from PAYE RTI"],
            ["UK, all industries, seasonally adjusted"],
            [None],
            ["Units", "Payrolled employees"],
            [None],
            header,
            ["January 2019", 10, 100, 200, 300, 400, 50, 1060],
            ["February 2019", 11, 110, 210, 310, 410, 55, 1106],
        ]
    )
    pay = pd.DataFrame(
        [
            ["29. Median pay from PAYE RTI"],
            ["UK, all industries, seasonally adjusted"],
            [None],
            ["Units", "GBP per month"],
            [None],
            header,
            ["January 2019", 50, 1000, 2000, 3000, 2500, 1200, 2100],
            ["February 2019", 55, 1100, 2200, 3300, 2600, 1250, 2200],
        ]
    )
    with pd.ExcelWriter(path) as writer:
        index.to_excel(writer, sheet_name="Index", header=False, index=False)
        employees.to_excel(writer, sheet_name="28. Employees (Age)", header=False, index=False)
        pay.to_excel(writer, sheet_name="29. Median pay (Age)", header=False, index=False)


def test_rti_parser_extracts_age_groups_and_flags_latest_month(tmp_path: Path) -> None:
    workbook = tmp_path / "rti.xlsx"
    _write_rti_workbook(workbook)

    parsed = parse_rti_age_workbook(workbook)

    assert {"Under 18", "18-24", "25-34", "35-49", "50-64", "65+"}.issubset(
        set(parsed["age_group"])
    )
    latest = parsed[parsed["date"].eq(pd.Timestamp("2019-02-01"))]
    assert latest["flash_or_provisional_flag"].all()
    assert parsed["source_release_date"].eq("2026-06-18").all()


def test_source_validation_reads_rti_median_pay_by_direct_cell(tmp_path: Path) -> None:
    workbook = tmp_path / "rti.xlsx"
    _write_rti_workbook(workbook)

    jan_2019 = _raw_rti_median_pay_cell(
        workbook,
        age_column="18 to 24",
        date=pd.Timestamp("2019-01-01"),
    )
    latest = _raw_rti_median_pay_cell(workbook, age_column="18 to 24", latest=True)

    assert jan_2019["raw_value"] == 1000.0
    assert jan_2019["cell"] == "C7"
    assert latest["date"] == pd.Timestamp("2019-02-01")
    assert latest["raw_value"] == 1100.0
    assert latest["cell"] == "C8"


def test_rti_jan_2019_real_pay_baseline_equals_100(tmp_path: Path) -> None:
    workbook = tmp_path / "rti.xlsx"
    _write_rti_workbook(workbook)
    rti = parse_rti_age_workbook(workbook)
    inflation = pd.DataFrame(
        [
            {"date": pd.Timestamp("2019-01-01"), "cpih_index_jan2019_100": 100.0},
            {"date": pd.Timestamp("2019-02-01"), "cpih_index_jan2019_100": 105.0},
        ]
    )

    real = compute_rti_real_pay(rti, inflation)
    baseline = real[real["date"].eq(pd.Timestamp("2019-01-01"))]

    assert set(baseline["real_pay_index_jan2019_100"].round(6)) == {100.0}
    assert set(baseline["payrolled_employees_index_jan2019_100"].round(6)) == {100.0}


def test_rti_triangulation_does_not_imply_25_34_ashe_match(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    tables = output_root / "tables"
    tables.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "age_group": "18-24",
                "latest_available_month": "2026-05-01",
                "real_pay_pct_change_since_jan2019": 6.22,
            },
            {
                "age_group": "25-34",
                "latest_available_month": "2026-05-01",
                "real_pay_pct_change_since_jan2019": 5.0,
            },
        ]
    ).to_csv(tables / "rti_age_real_pay_change.csv", index=False)
    pd.DataFrame(
        [
            {"age_group": "18-21", "latest_year": 2025, "real_pct_change": -1.81},
            {"age_group": "22-29", "latest_year": 2025, "real_pct_change": 3.57},
        ]
    ).to_csv(tables / "age_group_real_earnings_change.csv", index=False)
    mapping = tmp_path / "age_group_mapping.yaml"
    mapping.write_text(
        "\n".join(
            [
                "rti_to_ashe_comparison:",
                '  - rti_age_group: "18-24"',
                '    closest_ashe_groups: ["18-21", "22-29"]',
                '    comparison_quality: "imperfect"',
                '    note: "RTI 18-24 overlaps two ASHE age groups."',
                '  - rti_age_group: "25-34"',
                "    closest_ashe_groups: []",
                '    comparison_quality: "no exact ASHE wage match"',
                '    note: "RTI keeps a 25-34 band, but ASHE does not publish a matching wage row here."',
            ]
        ),
        encoding="utf-8",
    )

    path = build_rti_triangulation_report(output_root=output_root, mapping_config=mapping)
    text = path.read_text(encoding="utf-8")

    assert "RTI 25-34 -> ASHE no exact ASHE match" in text
    assert "RTI 25-34 -> ASHE 25-34" not in text


def test_ashe_decomposition_contributions_sum_to_weekly_log_change() -> None:
    raw = pd.DataFrame(
        [
            {
                "year": year,
                "age_group": age_group,
                "measure": measure,
                "median_value": value,
                "source_file": f"{year}.zip",
                "source_release": str(year),
            }
            for year, values in {
                2019: {
                    ("18-21", "weekly_gross"): 100.0,
                    ("18-21", "hourly_gross"): 10.0,
                    ("18-21", "total_paid_hours"): 10.0,
                    ("22-29", "weekly_gross"): 200.0,
                    ("22-29", "hourly_gross"): 20.0,
                    ("22-29", "total_paid_hours"): 10.0,
                },
                2025: {
                    ("18-21", "weekly_gross"): 121.0,
                    ("18-21", "hourly_gross"): 11.0,
                    ("18-21", "total_paid_hours"): 11.0,
                    ("22-29", "weekly_gross"): 242.0,
                    ("22-29", "hourly_gross"): 22.0,
                    ("22-29", "total_paid_hours"): 11.0,
                },
            }.items()
            for (age_group, measure), value in values.items()
        ]
    )
    inflation = pd.DataFrame(
        [
            {"year": 2019, "cpih_index_2019_100": 100.0},
            {"year": 2025, "cpih_index_2019_100": 110.0},
        ]
    )

    annual, summary = compute_decomposition(raw, inflation)

    assert set(annual[annual["year"].eq(2019)]["real_weekly_earnings_index_2019_100"]) == {
        100.0
    }
    row = summary[summary["age_group"].eq("18-21")].iloc[0]
    parts = (
        row["hourly_log_contribution"]
        + row["hours_log_contribution"]
        + row["residual_log_contribution"]
    )
    assert parts == pytest.approx(row["weekly_log_change"], abs=1e-5)


def test_ashe_decomposition_availability_lists_missing_required_workbooks(tmp_path: Path) -> None:
    zip_path = tmp_path / "ashetable62025provisional.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr("PROV - Age Group Table 6.1a   Weekly pay - Gross 2025.xlsx", "")

    availability = inspect_ashe_decomposition_availability(tmp_path)

    missing = availability[~availability["available"]]
    assert {"hourly_gross", "total_paid_hours"}.issubset(set(missing["measure"]))


def test_ashe_decomposition_report_names_missing_requested_focus_groups(tmp_path: Path) -> None:
    availability = pd.DataFrame(
        [
            {"measure": "weekly_gross", "available": True},
            {"measure": "hourly_gross", "available": True},
            {"measure": "total_paid_hours", "available": True},
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "age_group": age_group,
                "weekly_pct_change": 1.0,
                "hourly_log_contribution": 0.02,
                "hours_log_contribution": -0.01,
                "residual_log_contribution": 0.0,
                "weekly_log_change": 0.01,
            }
            for age_group in ["18-21", "22-29", "30-39"]
        ]
    )

    path = write_decomposition_report(availability, summary, evidence_root=tmp_path)
    text = path.read_text(encoding="utf-8")

    assert "Requested ASHE decomposition groups: 18-21, 22-29, 25-34, 30-39." in text
    assert "Computed decomposition groups: 18-21, 22-29, 30-39." in text
    assert "25-34: unavailable in the parsed ASHE Table 6 age rows" in text


def test_minimum_wage_rates_include_2019_2024_2025_and_2026() -> None:
    html = """
    <table><thead><tr><td></td><th scope="col">21 and over</th><th scope="col">18 to 20</th><th scope="col">Under 18</th><th scope="col">Apprentice</th></tr></thead>
    <tbody><tr><th scope="row">April 2026</th><td>£12.71</td><td>£10.85</td><td>£8</td><td>£8</td></tr>
    <tr><th scope="row">April 2025 to March 2026</th><td>£12.21</td><td>£10</td><td>£7.55</td><td>£7.55</td></tr>
    <tr><th scope="row">April 2024 to March 2025</th><td>£11.44</td><td>£8.60</td><td>£6.40</td><td>£6.40</td></tr></tbody></table>
    <table><thead><tr><td></td><th scope="col">25 and over</th><th scope="col">21 to 24</th><th scope="col">18 to 20</th><th scope="col">Under 18</th><th scope="col">Apprentice</th></tr></thead>
    <tbody><tr><th scope="row">April 2019 to March 2020</th><td>£8.21</td><td>£7.70</td><td>£6.15</td><td>£4.35</td><td>£3.90</td></tr></tbody></table>
    """

    rates = parse_minimum_wage_html(html)

    assert {2019, 2024, 2025, 2026}.issubset(set(rates["effective_year"]))
    assert rates[
        rates["effective_year"].eq(2026) & rates["age_band"].eq("18 to 20")
    ].iloc[0]["nominal_hourly_rate"] == 10.85


def test_minimum_wage_json_extracts_the_official_details_body(tmp_path: Path) -> None:
    source = tmp_path / "minimum_wage.json"
    body = "<table><tr><th scope='row'>April 2026</th><td>£10.85</td></tr></table>"
    source.write_text(
        json.dumps({"base_path": "/national-minimum-wage-rates", "details": {"body": body}}),
        encoding="utf-8",
    )

    assert minimum_wage.read_minimum_wage_html(source) == body
    assert source_validation._read_minimum_wage_html(source) == body


def test_minimum_wage_json_requires_a_nonempty_details_body(tmp_path: Path) -> None:
    source = tmp_path / "minimum_wage.json"
    source.write_text(json.dumps({"details": {"body": ""}}), encoding="utf-8")

    with pytest.raises(ValueError, match="details.body"):
        minimum_wage.read_minimum_wage_html(source)
    with pytest.raises(ValueError, match="details.body"):
        source_validation._read_minimum_wage_html(source)


def test_minimum_wage_build_ignores_download_metadata_json(tmp_path: Path) -> None:
    source = tmp_path / "current" / "minimum_wage.json"
    source.parent.mkdir(parents=True)
    body = """
    <table><thead><tr><th scope="col">18 to 20</th></tr></thead>
    <tbody><tr><th scope="row">April 2026</th><td>£10.85</td></tr></tbody></table>
    """
    source.write_text(json.dumps({"details": {"body": body}}), encoding="utf-8")
    source.with_suffix(".json.metadata.json").write_text("{}", encoding="utf-8")

    rates = minimum_wage.build_minimum_wage_rates(tmp_path)

    assert len(rates) == 1
    assert rates.iloc[0]["nominal_hourly_rate"] == 10.85


def test_source_validation_reads_minimum_wage_cells_without_project_parser() -> None:
    html = """
    <table><thead><tr><td></td><th scope="col">21 and over</th><th scope="col">18 to 20</th><th scope="col">Under 18</th><th scope="col">Apprentice</th></tr></thead>
    <tbody><tr><th scope="row">April 2026</th><td>Â£12.71</td><td>Â£10.85</td><td>Â£8</td><td>Â£8</td></tr></tbody></table>
    <table><thead><tr><td></td><th scope="col">25 and over</th><th scope="col">21 to 24</th><th scope="col">18 to 20</th><th scope="col">Under 18</th><th scope="col">Apprentice</th></tr></thead>
    <tbody><tr><th scope="row">April 2019 to March 2020</th><td>Â£8.21</td><td>Â£7.70</td><td>Â£6.15</td><td>Â£4.35</td><td>Â£3.90</td></tr></tbody></table>
    """

    rate_2019 = _raw_minimum_wage_rate_cell(
        html,
        period_label="April 2019 to March 2020",
        age_band="18 to 20",
    )
    rate_2026 = _raw_minimum_wage_rate_cell(
        html,
        period_label="April 2026",
        age_band="18 to 20",
    )

    assert rate_2019["raw_value"] == 6.15
    assert rate_2019["table_index"] == 2
    assert rate_2026["raw_value"] == 10.85
    assert rate_2026["table_index"] == 1


def test_minimum_wage_real_rates_and_bite_skip_without_ashe_hourly(tmp_path: Path) -> None:
    rates = pd.DataFrame(
        [
            {
                "effective_year": 2019,
                "effective_date": pd.Timestamp("2019-04-01"),
                "period_label": "April 2019 to March 2020",
                "age_band": "18 to 20",
                "policy_series": "18 to 20",
                "nominal_hourly_rate": 6.15,
                "source_file": "toy.html",
                "source_url": "https://www.gov.uk/national-minimum-wage-rates",
            },
            {
                "effective_year": 2026,
                "effective_date": pd.Timestamp("2026-04-01"),
                "period_label": "April 2026",
                "age_band": "18 to 20",
                "policy_series": "18 to 20",
                "nominal_hourly_rate": 10.85,
                "source_file": "toy.html",
                "source_url": "https://www.gov.uk/national-minimum-wage-rates",
            },
        ]
    )
    inflation = pd.DataFrame(
        [
            {"year": 2019, "cpih_april_index": 100.0},
            {"year": 2026, "cpih_april_index": 125.0},
        ]
    )

    real = compute_real_minimum_wage_rates(rates, inflation)
    bite = compute_minimum_wage_bite(real, tmp_path)

    baseline = real[real["effective_year"].eq(2019)].iloc[0]
    assert baseline["real_statutory_wage_index_2019_100"] == pytest.approx(100.0)
    assert bite.iloc[0]["calculation_status"] == "skipped"
    assert "unavailable" in bite.iloc[0]["note"]


def test_non_robustness_required_claims_are_source_bounded(tmp_path: Path) -> None:
    matrix = pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "spec_tier": "core",
                "baseline_real_pct_change": -1.0,
                "real_pct_change": -1.0,
                "difference_from_baseline": 0.0,
                "sign_flip_vs_baseline": False,
                "material_disagreement": False,
            }
        ]
    )
    path = assess_claims(
        [
            {
                "claim_id": "context",
                "text": "Minimum wage changes provide policy context.",
                "population": "young workers",
                "outcome": "wage floor",
                "spec_tier": "context",
                "robustness_required": False,
            }
        ],
        matrix,
        tmp_path,
    )

    result = pd.read_csv(path)
    assert result.iloc[0]["verdict"] == "descriptive / source-bounded"
    assert result.iloc[0]["specifications_tested"] == 0


def test_v2_claim_wording_keeps_decomposition_descriptive() -> None:
    claims_text = Path("config/claims.yaml").read_text(encoding="utf-8")
    research_note_text = Path("reports/research_note.md").read_text(encoding="utf-8")

    assert "explained by hourly pay" not in claims_text
    assert "explanation module" not in research_note_text
    assert "can be decomposed" in claims_text


def test_source_validation_requires_adult_threshold_minimum_wage_checks() -> None:
    assert "minimum_wage_adult_threshold_2019_rate" in REQUIRED_SOURCE_CHECKS
    assert "minimum_wage_adult_threshold_latest_ashe_year_rate" in REQUIRED_SOURCE_CHECKS


def test_research_note_is_generated_from_current_outputs(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    tables = output_root / "tables"
    evidence = output_root / "evidence"
    tables.mkdir(parents=True)
    evidence.mkdir(parents=True)
    pd.DataFrame(
        [
            {"age_group": "16-17", "latest_year": 2025, "real_pct_change": 0.5},
            {"age_group": "18-21", "latest_year": 2025, "real_pct_change": -9.99},
            {"age_group": "22-29", "latest_year": 2025, "real_pct_change": 3.57},
            {"age_group": "30-39", "latest_year": 2025, "real_pct_change": 4.05},
            {"age_group": "60+", "latest_year": 2025, "real_pct_change": 10.26},
        ]
    ).to_csv(tables / "age_group_real_earnings_change.csv", index=False)
    pd.DataFrame(
        [
            {
                "age_group": "18-24",
                "latest_available_month": "2026-05-01",
                "latest_non_flash_month": "2026-04-01",
                "real_pay_pct_change_since_jan2019": 6.22,
                "employee_count_pct_change_since_jan2019": -2.86,
            }
        ]
    ).to_csv(tables / "rti_age_real_pay_change.csv", index=False)
    pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "latest_year": 2025,
                "weekly_pct_change": -9.99,
                "hourly_pct_change": 15.33,
                "hours_pct_change": -20.4,
                "hourly_log_contribution": 0.143,
                "hours_log_contribution": -0.228,
                "residual_log_contribution": 0.067,
            },
            {
                "age_group": "22-29",
                "latest_year": 2025,
                "weekly_pct_change": 3.57,
                "hourly_pct_change": 4.45,
                "hours_pct_change": -0.53,
                "hourly_log_contribution": 0.044,
                "hours_log_contribution": -0.005,
                "residual_log_contribution": -0.003,
            },
        ]
    ).to_csv(tables / "ashe_hours_decomposition.csv", index=False)
    pd.DataFrame(
        [
            {
                "effective_year": 2019,
                "policy_series": "18 to 20",
                "nominal_hourly_rate": 6.15,
                "real_statutory_wage_index_2019_100": 100.0,
            },
            {
                "effective_year": 2026,
                "policy_series": "18 to 20",
                "nominal_hourly_rate": 10.85,
                "real_statutory_wage_index_2019_100": 133.87,
            },
        ]
    ).to_csv(tables / "minimum_wage_real_rates.csv", index=False)
    pd.DataFrame(
        [
            {
                "year": 2019,
                "ashe_age_group": "18-21",
                "minimum_wage_bite": 0.721,
            },
            {
                "year": 2025,
                "ashe_age_group": "18-21",
                "minimum_wage_bite": 0.794,
            },
            {
                "year": 2019,
                "ashe_age_group": "22-29",
                "minimum_wage_bite": 0.691,
            },
            {
                "year": 2025,
                "ashe_age_group": "22-29",
                "minimum_wage_bite": 0.769,
            },
        ]
    ).to_csv(tables / "minimum_wage_bite_by_age.csv", index=False)
    pd.DataFrame(
        [
            {
                "date": "2026-04-30",
                "youth_unemployment_gap_change_since_2019": 3.7,
                "youth_inactivity_gap_change_since_2019": 2.68,
            }
        ]
    ).to_csv(tables / "youth_labour_market_gaps.csv", index=False)
    pd.DataFrame(
        [
            {
                "age_group": "18-21",
                "spec_tier": "core",
                "material_disagreements": 3,
                "specifications_tested": 6,
                "assessment": "not robust",
            }
        ]
    ).to_csv(evidence / "fragility_scores.csv", index=False)

    path = build_research_note(output_root=output_root, reports_root=tmp_path / "reports")
    text = path.read_text(encoding="utf-8")

    assert "-9.99%" in text
    assert "real median monthly pay rose by 6.22%" in text
    assert "The ASHE decomposition helps explain the ASHE weekly-earnings result" in text
    assert "RTI adds a separate monthly PAYE check for the wider 18-24 group" in text
    assert "The ASHE decomposition shows how both can be true" not in text
    assert "25-34 is a labour-market comparator, not an ASHE wage comparator" in text
    assert "The configured robustness verdict is not robust: 3 of 6" in text
    assert "## 4. Why The 18-21 Result Is Not Robust" in text
    assert "That finding is fragile" not in text
    assert 1500 <= len(text.split()) <= 2500
