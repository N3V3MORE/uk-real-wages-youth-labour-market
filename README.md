# Real Wages and Youth Labour Market Stress in the UK, 2019-2026

This repo asks a narrow question: have UK workers, especially younger workers, become better or worse off after inflation since 2019? It rebuilds official sources from raw downloads and checks whether the answer changes when the source, deflator, baseline year, earnings measure, hours, or worker definition changes.

![Dashboard screenshot](docs/dashboard-screenshot.png)

## Main Finding

The 18-21 result should not be sold as a clean gain or loss. In the baseline ASHE CPIH run, 18-21 real earnings are down from 2019 to 2025, but that conclusion moves under reasonable alternative specifications. The safest reading is that the youngest-worker result is fragile and specification-dependent.

The 22-29 result is steadier. RTI, A05, EARN01, ASHE hours, and minimum wage rates add context, but they do not replace ASHE. RTI is monthly PAYE age-pay evidence. A05 is labour-market status. EARN01 is monthly whole-economy pay, not age-specific pay. Minimum wage rates are policy context, not proof of cause.

## What The Pipeline Does

- Downloads ONS MM23, ASHE, PAYE RTI, A05 SA, EARN01, and GOV.UK minimum wage files into `data/raw`.
- Cleans raw files into long parquet tables under `data/processed`.
- Deflates ASHE earnings with CPIH by default and CPI as a sensitivity check.
- Builds age-group, region-age, RTI, ASHE decomposition, minimum wage, youth labour-market, and monthly AWE outputs.
- Writes charts, source-value checks, fragility diagnostics, final claims, and a Streamlit dashboard.

## Rebuild It

Create the environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install -e .
```

Run everything:

```powershell
make all
```

On Windows without `make`, run the same steps directly:

```powershell
.\.venv\Scripts\python -m uk_wages.download
.\.venv\Scripts\python -m uk_wages.clean_cpi
.\.venv\Scripts\python -m uk_wages.clean_ashe
.\.venv\Scripts\python -m uk_wages.clean_region_ashe
.\.venv\Scripts\python -m uk_wages.clean_a05
.\.venv\Scripts\python -m uk_wages.clean_earn01
.\.venv\Scripts\python -m uk_wages.clean_rti
.\.venv\Scripts\python -m uk_wages.ashe_decomposition
.\.venv\Scripts\python -m uk_wages.minimum_wage
.\.venv\Scripts\python -m uk_wages.analysis
.\.venv\Scripts\python -m uk_wages.rti_analysis
.\.venv\Scripts\python -m uk_wages.charts
.\.venv\Scripts\python -m uk_wages.rti_triangulation
.\.venv\Scripts\python -m uk_wages.robustness --run-all
.\.venv\Scripts\python -m uk_wages.source_validation
.\.venv\Scripts\python -m uk_wages.triangulation
.\.venv\Scripts\python -m uk_wages.final_claims
.\.venv\Scripts\python -m uk_wages.research_note
.\.venv\Scripts\python -m uk_wages.robustness --contrarian
.\.venv\Scripts\python -m uk_wages.evidence --build-report
.\.venv\Scripts\python -m pytest
```

Launch the dashboard:

```powershell
.\.venv\Scripts\python -m streamlit run dashboard/app.py
```

## Files Worth Opening

- `dashboard/app.py` - Streamlit dashboard.
- `reports/policy_brief.md` - short result summary.
- `reports/research_note.md` - longer v2 research note.
- `reports/methodology.md` - data choices and transformations.
- `docs/v2_expansion_plan.md` - source-role guardrails for the triangulation upgrade.
- `outputs/tables` - generated summary tables.
- `outputs/charts` - generated PNG charts.
- `outputs/evidence/source_value_checks.csv` - raw-to-processed spot checks.
- `outputs/evidence/final_claims.md` - qualified claim wording.
- `outputs/evidence/fragility_diagnostics.md` - why the 18-21 result is unstable.
- `outputs/evidence/rti_ashe_triangulation.md` - how RTI 18-24 compares with ASHE 18-21 and 22-29.
- `outputs/evidence/ashe_decomposition_report.md` - hourly pay versus hours split.
- `outputs/evidence/minimum_wage_context.md` - statutory wage-floor context.

Generated data and outputs are ignored by git. Rebuild them with the commands above.

## Checks After Rebuild

- `pytest` should pass.
- `outputs/evidence/source_value_checks.csv` should show 17 passing checks.
- RTI Jan 2019 indices should equal 100 where data exist.
- `outputs/evidence/final_claims.md` should keep the 18-21 result qualified.
- `outputs/charts` should contain generated PNG charts.
- `reports/policy_brief.md` should not describe the ASHE result as a 2026 age-specific wage finding.

## Boundaries

ASHE is annual and age-specific. In the current source set, the latest ASHE age-specific wage year is 2025 provisional. The project title includes 2026 because MM23, RTI, A05 SA, EARN01, and minimum wage rates currently extend into 2026, but those sources do not provide 2026 age-specific ASHE wages.

RTI is PAYE administrative data. It covers payrolled employees, not self-employment or all income. It measures monthly pay, not ASHE weekly or hourly earnings. The latest RTI month is revision-prone.

This is descriptive analysis. It does not identify causal effects.
