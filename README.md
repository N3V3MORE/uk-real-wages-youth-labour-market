# Real Wages and Youth Labour Market Stress in the UK, 2019-2026

This repository builds a reproducible command-line pipeline for the question:

> Have UK workers, especially younger workers, actually become better or worse off after inflation since 2019?

The project uses official ONS sources only. Annual age-specific earnings use ASHE, so the age-specific wage analysis runs from 2019 to the latest available ASHE year. Monthly whole-economy wage trends use EARN01 and can extend into 2026. Labour-market stress indicators use A05 SA.

## Reproduce

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install -e .
```

Run the pipeline:

```powershell
make all
```

If `make` is not available on the machine, run the same steps directly:

```powershell
.\.venv\Scripts\python -m uk_wages.download
.\.venv\Scripts\python -m uk_wages.clean_cpi
.\.venv\Scripts\python -m uk_wages.clean_ashe
.\.venv\Scripts\python -m uk_wages.clean_region_ashe
.\.venv\Scripts\python -m uk_wages.clean_a05
.\.venv\Scripts\python -m uk_wages.clean_earn01
.\.venv\Scripts\python -m uk_wages.analysis
.\.venv\Scripts\python -m uk_wages.charts
.\.venv\Scripts\python -m pytest
```

## Outputs

- Processed data: `data/processed`
- Charts: `outputs/charts`
- Final tables: `outputs/tables`
- Methodology: `reports/methodology.md`
- Policy brief: `reports/policy_brief.md`

## Data Reality

The project title includes 2019-2026 because inflation, EARN01, and A05 SA have current 2026 releases. Age-specific earnings rely on ASHE, and the latest ASHE edition currently available is the 2025 provisional release. The pipeline therefore avoids claiming 2026 age-specific wage results unless ASHE 2026 becomes available.

## Robustness and Evidence Harness

The evidence harness lets an analyst or model propose experiment YAML files, but only inside a validated menu of assumptions. It does not execute arbitrary Python.

Run one experiment:

```powershell
.\.venv\Scripts\python -m uk_wages.experiment_runner --spec experiments/baseline.yaml
```

Run the full evidence suite:

```powershell
.\.venv\Scripts\python -m uk_wages.robustness --run-all
.\.venv\Scripts\python -m uk_wages.evidence --build-report
.\.venv\Scripts\python -m uk_wages.robustness --contrarian
.\.venv\Scripts\python -m uk_wages.triangulation
```

Outputs:

- `outputs/experiments/<experiment_name>/age_group_real_earnings.csv`
- `outputs/experiments/<experiment_name>/comparison_vs_baseline.csv`
- `outputs/experiments/<experiment_name>/evidence_card.md`
- `outputs/evidence/robustness_matrix.csv`
- `outputs/evidence/fragility_scores.csv`
- `outputs/evidence/evidence_report.md`
- `outputs/evidence/contrarian_findings.md`
- `outputs/evidence/triangulation_report.md`

The dashboard includes a `Robustness and evidence` tab once those outputs exist.
