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
- `outputs/evidence/ashe_decomposition_report.md` names 25-34 as unavailable for ASHE decomposition, rather than fabricating a row.
- `config/sources.lock.yaml` records the locked source URLs, downloaded file paths, release labels, SHA256 hashes, download timestamps, and source file shapes used for release reproduction.

## CI Checks

The default CI workflow runs unit tests on push and pull request. The manual `Full pipeline smoke` workflow in GitHub Actions runs `python -m uk_wages.pipeline --all` when a reviewer wants an end-to-end rebuild check without making every push depend on live ONS/GOV.UK availability.

## Claims To Challenge

- Do not treat the 18-21 baseline loss as a clean finding. It changes under baseline-year, mean-vs-median, and full-time-only choices.
- Do not treat RTI 18-24 as the same population as ASHE 18-21.
- Do not treat minimum-wage rates as causal evidence. They are wage-floor context.
- Do not treat the project title's 2026 endpoint as ASHE 2026 age-specific wage evidence. The 2026 evidence comes from non-ASHE sources.

## Dashboard Check

Run:

```powershell
.\.venv\Scripts\python -m streamlit run dashboard/app.py
```

The dashboard should show the final claim wording, robustness tables, RTI triangulation, ASHE decomposition, minimum-wage context, labour-market stress, and source validation outputs.
