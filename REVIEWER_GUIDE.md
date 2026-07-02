# Reviewer Guide

## Question

Have UK workers, especially younger workers, become better or worse off after inflation since 2019?

This repo answers that as a descriptive data exercise. It does not try to estimate causes or forecast wages.

## Data Used

- ONS MM23 CPIH and CPI time-series data.
- ONS ASHE Table 6 age-group earnings.
- ONS ASHE UK region by age group.
- ONS A05 SA labour-market data for unemployment and inactivity context.
- ONS EARN01 average weekly earnings for monthly whole-economy pay context.

The current age-specific wage result stops at ASHE 2025 provisional. EARN01 and A05 extend into 2026, but neither is age-specific wage evidence.

## Cold Run

Create a virtual environment, install the project, and run:

```powershell
make all
```

If `make` is not available on Windows:

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

## Checks That Matter

After a successful run, inspect:

- `outputs/evidence/source_value_checks.csv` - should show 11 passing checks.
- `outputs/evidence/final_claims.md` - should keep the 18-21 result qualified.
- `outputs/evidence/claim_assessment.csv` - should mark the youngest-worker claim as fragile.
- `outputs/evidence/fragility_diagnostics.md` - should show which assumptions move the result.
- `outputs/charts` - should contain generated PNG charts.
- `reports/policy_brief.md` - should not describe the ASHE result as a 2026 age-specific wage finding.

Launch the dashboard with:

```powershell
.\.venv\Scripts\python -m streamlit run dashboard/app.py
```

Open the local Streamlit URL and check the `Robustness and evidence` tab.

## Result To Keep

The baseline ASHE CPIH analysis is useful, but it is not enough for a clean young-worker headline. The 18-21 result changes under defensible choices for baseline year, earnings measure, and worker definition, so it should be described as ambiguous rather than as a clear gain or loss.

The 22-29 result is more stable. A05 and EARN01 are useful context, but they answer different questions.

## Known Limits

- ASHE is annual and age-specific.
- ASHE 2026 is not part of the current age-specific wage result.
- EARN01 is monthly, but it is whole-economy or sector-level, not age-specific.
- A05 SA is labour-market status, not earnings.
- The project derives A05 16-24 values by combining 16-17 and 18-24 component levels.
- ONS labels A05 SA as official statistics in development.
- The analysis is descriptive and does not identify causal mechanisms.
