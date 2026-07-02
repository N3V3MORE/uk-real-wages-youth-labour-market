# Reviewer Guide

This guide is for someone checking whether the repo's conclusion is supported by the data and rebuild steps.

## Start Here

Read `reports/research_note.md` first. It is the main written interpretation. Use `reports/policy_brief.md` only as the short summary.

Then read `reports/methodology.md` for source roles and boundaries. The important boundary is that ASHE supplies the annual age-specific wage result through 2025 provisional; RTI, A05, EARN01, and minimum-wage rates add current or contextual evidence, but they do not replace ASHE.

## Rebuild Path

Run the cross-platform pipeline runner from a fresh checkout:

```powershell
.\.venv\Scripts\python -m uk_wages.pipeline --all
```

When `make` is available, `make all` runs the same pipeline. For release reproduction against the committed source hashes, run:

```powershell
.\.venv\Scripts\python -m uk_wages.pipeline --all --locked
```

After rebuild, check:

- `pytest` passes.
- `outputs/evidence/source_value_checks.csv` has 17 passing checks.
- `outputs/evidence/manual_validation_audit.md` includes direct-cell RTI checks and direct GOV.UK minimum-wage table checks.
- `outputs/evidence/claim_assessment.csv` marks the 18-21 result as fragile.
- `outputs/evidence/triangulation_summary.csv` keeps ASHE age groups separate when comparing with whole-economy EARN01.
- `outputs/evidence/rti_ashe_annual_summary.csv` reports April-to-April RTI-ASHE directional concordance for overlapping years.
- `outputs/evidence/ashe_decomposition_report.md` names 25-34 as unavailable for ASHE decomposition, rather than fabricating a row, and reports year-by-year residual diagnostics.
- `outputs/evidence/ashe_quality_availability.md` records which ASHE CV, quality, suppression, and reliability fields were checked.
- `outputs/evidence/ashe_uncertainty_bands.md` uses published CVs only as approximate two-CV sensitivity bands, not confidence intervals.
- `outputs/evidence/ashe_composition_audit.md` separates work-status, sex-split, hours, and job-count composition evidence from wage evidence.
- `outputs/evidence/claim_confidence.md` gives each headline claim a plain-English confidence label.
- `outputs/evidence/headline_number_lineage.csv` maps headline numbers back to source files, processed files, modules, and validation checks.
- `config/sources.lock.yaml` records the locked source URLs, downloaded file paths, release labels, SHA256 hashes, download timestamps, and source file shapes used for release reproduction.

## CI Checks

The default CI workflow runs unit tests on push and pull request. The manual `Full pipeline smoke` workflow in GitHub Actions runs `python -m uk_wages.pipeline --all` when a reviewer wants an end-to-end rebuild check without making every push depend on live ONS/GOV.UK availability.

## Claims To Challenge

- Do not treat the 18-21 baseline loss as a clean finding. It changes under baseline-year, mean-vs-median, and full-time-only choices.
- Do not treat RTI 18-24 as the same population as ASHE 18-21.
- Do not treat minimum-wage rates as causal evidence. They are wage-floor context.
- Do not treat the project title's 2026 endpoint as ASHE 2026 age-specific wage evidence. The 2026 evidence comes from non-ASHE sources.
- Do not turn ASHE CV fields into confidence intervals. The project may use them for approximate two-CV sensitivity bands, but those bands are not source-supplied intervals.

## What Would Change The Conclusion?

The 18-21 claim would become stronger if ASHE quality evidence remains reliable, the negative weekly-earnings result survives the core specifications, hourly pay, weekly pay, RTI, and full-time rows all point in the same direction, and composition checks do not explain the movement away.

It would become weaker if ASHE quality flags are poor, the negative result disappears under full-time-only or mean earnings, the result is mostly a paid-hours story, or RTI continues to point differently for the wider 18-24 PAYE group.

The 22-29 claim would become stronger if quality flags remain reliable and robustness checks keep agreeing. It would weaken if source quality, work-status splits, or triangulation checks move away from the baseline ASHE result.

## Dashboard Check

Run:

```powershell
.\.venv\Scripts\python -m streamlit run dashboard/app.py
```

The dashboard should show the final claim wording, robustness tables, RTI triangulation, ASHE decomposition, ASHE quality and composition audits, minimum-wage context, labour-market stress, claim confidence, lineage, and source validation outputs.
