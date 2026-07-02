# Reviewer Guide

## 1. Research question

Have UK workers, especially younger workers, become better or worse off after inflation since 2019?

The project is a reproducible descriptive analysis. It does not make causal or forecasting claims.

## 2. Data sources

- ONS MM23 CPIH/CPI time-series data for inflation deflation.
- ONS ASHE Table 6 age-group earnings for annual age-specific pay.
- ONS A05 SA labour-market data for youth unemployment and inactivity context.
- ONS EARN01 average weekly earnings for current monthly whole-economy wage trends.

The latest age-specific wage evidence is ASHE 2025 provisional in the current downloaded source set. EARN01 and A05 extend further into 2026, but they are not age-specific ASHE wage evidence.

## 3. How to run the pipeline

Install the project in a virtual environment, then run:

```powershell
make all
```

If `make` is not available on Windows, run:

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

## 4. Main outputs

- Final tables: `outputs/tables`
- Charts: `outputs/charts`
- Policy brief: `reports/policy_brief.md`
- Methodology: `reports/methodology.md`
- Dashboard app: `dashboard/app.py`
- Evidence package: `outputs/evidence`

## 5. Main conclusion

The baseline ASHE CPIH analysis is useful but not enough on its own for a clean young-worker headline. The 18-21 real-earnings finding is specification-dependent and should be described as ambiguous rather than as a clear gain or loss.

The project’s stronger conclusion is methodological: post-2019 real-earnings statements depend on deflator choice, baseline year, earnings measure, and worker definition. The repo makes those assumptions explicit and testable.

## 6. Robustness and fragility finding

The robustness harness runs a fixed menu of validated specifications, not arbitrary generated code. It separates core specifications from stress tests and reports material disagreements separately from near-zero sign flips.

Key evidence files:

- `outputs/evidence/robustness_matrix.csv`
- `outputs/evidence/fragility_scores.csv`
- `outputs/evidence/one_way_sensitivity.csv`
- `outputs/evidence/minimal_flip_specs.csv`
- `outputs/evidence/fragility_diagnostics.md`
- `outputs/evidence/contrarian_findings.md`
- `outputs/evidence/final_claims.md`

For 18-21, the final claim should remain qualified: the result changes under reasonable alternative assumptions, so the evidence does not support a simple claim that the youngest workers clearly became better or worse off.

## 7. Manual source-value audit

The file `outputs/evidence/source_value_checks.csv` spot-checks selected processed values against downloaded raw ONS files. The companion audit, `outputs/evidence/manual_validation_audit.md`, records raw file paths, sheet or table names, row or series identifiers, raw values, processed values, differences, status, and notes.

This is intentionally small. It checks the values most likely to reveal a wrong series, wrong sheet, wrong unit, or wrong age-group selection.

## 8. Known limitations

- ASHE is annual and age-specific; it does not provide a current monthly 2026 age-specific wage result.
- EARN01 is monthly and current, but it is whole-economy or sector-level, not age-specific.
- A05 SA is labour-market stress context, not earnings evidence.
- A05 16-24 values are derived from component age groups in this project.
- The analysis is descriptive and does not identify causal mechanisms.

## 9. How to inspect the dashboard

Run:

```powershell
.\.venv\Scripts\python -m streamlit run dashboard/app.py
```

Then open the local Streamlit URL. The `Robustness and evidence` tab includes the robustness matrix, fragility scores, one-way sensitivity, minimal flip diagnostics, claim assessment, final claims, source validation, and contrarian findings.

## 10. Technical demonstration

This project demonstrates a complete reproducible data workflow: source download, cleaning, transformation, charting, dashboarding, robustness diagnostics, source-value validation, and reviewer-facing evidence packaging.
