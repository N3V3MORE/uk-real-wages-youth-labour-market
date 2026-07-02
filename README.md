# Real Wages and Youth Labour Market Stress in the UK, 2019-2026

This repo asks a narrow question: have UK workers, especially younger workers, become better or worse off after inflation since 2019? It uses ONS data only, rebuilds the data from raw downloads, and checks whether the headline changes when the deflator, baseline year, earnings measure, or worker definition changes.

![Dashboard screenshot](docs/dashboard-screenshot.png)

## Main Finding

The 18-21 result should not be sold as a clean gain or loss. In the baseline ASHE CPIH run, 18-21 real earnings are down from 2019 to 2025, but that conclusion moves under reasonable alternative specifications. The safest reading is that the youngest-worker result is fragile and specification-dependent.

The 22-29 result is steadier. A05 and EARN01 add context, but they do not replace ASHE: A05 is labour-market status, and EARN01 is monthly whole-economy pay, not age-specific pay.

## What The Pipeline Does

- Downloads ONS MM23, ASHE, A05 SA, and EARN01 files into `data/raw`.
- Cleans raw files into long parquet tables under `data/processed`.
- Deflates ASHE earnings with CPIH by default and CPI as a sensitivity check.
- Builds age-group, region-age, youth labour-market, and monthly AWE outputs.
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
.\.venv\Scripts\python -m uk_wages.analysis
.\.venv\Scripts\python -m uk_wages.charts
.\.venv\Scripts\python -m uk_wages.robustness --run-all
.\.venv\Scripts\python -m uk_wages.source_validation
.\.venv\Scripts\python -m uk_wages.triangulation
.\.venv\Scripts\python -m uk_wages.final_claims
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
- `reports/methodology.md` - data choices and transformations.
- `REVIEWER_GUIDE.md` - cold-run review path.
- `outputs/tables` - generated summary tables.
- `outputs/charts` - generated PNG charts.
- `outputs/evidence/source_value_checks.csv` - raw-to-processed spot checks.
- `outputs/evidence/final_claims.md` - qualified claim wording.
- `outputs/evidence/fragility_diagnostics.md` - why the 18-21 result is unstable.

Generated data and outputs are ignored by git. Rebuild them with the commands above.

## Boundaries

ASHE is annual and age-specific. In the current source set, the latest ASHE age-specific wage year is 2025 provisional. The project title includes 2026 because MM23, A05 SA, and EARN01 currently extend into 2026, but those sources do not provide 2026 age-specific ASHE wages.

This is descriptive analysis. It does not identify causal effects.
