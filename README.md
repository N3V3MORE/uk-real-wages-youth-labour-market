# Real Wages and Youth Labour Market Stress in the UK, 2019-2026

This repo asks a narrow question: have UK workers, especially younger workers, become better or worse off after inflation since 2019? It rebuilds official sources from raw downloads and checks whether the answer changes when the source, deflator, baseline year, earnings measure, hours, or worker definition changes.

![Dashboard screenshot](docs/dashboard-screenshot.png)

## Main Finding

The 18-21 result should not be sold as a clean gain or loss. In the baseline ASHE CPIH run, 18-21 real earnings are down from 2019 to 2025, but that conclusion moves under reasonable alternative specifications. The configured verdict is not robust: three of six core alternatives materially disagree, so the youngest-worker result is specification-dependent.

The 22-29 result is steadier. RTI, A05, EARN01, ASHE hours, and minimum wage rates add context, but they do not replace ASHE. RTI is monthly PAYE age-pay evidence. A05 is labour-market status. EARN01 is monthly whole-economy pay, not age-specific pay. Minimum wage rates are policy context, not proof of cause.

## What The Pipeline Does

- Downloads ONS MM23, ASHE, PAYE RTI, A05 SA, EARN01, and GOV.UK minimum wage files into `data/raw`.
- Cleans raw files into long parquet tables under `data/processed`.
- Deflates ASHE earnings with CPIH by default and CPI as a sensitivity check.
- Builds age-group, region-age, RTI, ASHE decomposition, ASHE quality, ASHE composition, minimum wage, youth labour-market, monthly AWE, and Option B modelling outputs.
- Writes charts, triangulation metrics, ASHE approximate CV bands, source-value checks, fragility diagnostics, claim confidence, headline lineage, final claims, and a Streamlit dashboard.

## Rebuild It

Create the environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -c requirements.lock
.\.venv\Scripts\python -m pip install --no-build-isolation --no-deps -e .
```

Run everything:

```powershell
.\.venv\Scripts\python -m uk_wages.pipeline --all
```

If `make` is available, this is equivalent to:

```powershell
make all
```

For release reproduction against the committed source lockfile:

```powershell
.\.venv\Scripts\python -m uk_wages.pipeline --all --locked
```

The locked rebuild runs the full analysis, the test suite, and the release packager. Its
reviewer-facing output is `releases/v2/evidence`. The package includes the source and
dependency lockfiles; raw workbooks, processed parquet files, and charts remain rebuild-only.

Run the same lint, type, and coverage gates used by CI:

```powershell
make quality
```

Without `make`, run:

```powershell
.\.venv\Scripts\python -m ruff check
.\.venv\Scripts\python -m mypy src
.\.venv\Scripts\python -m pytest --cov=uk_wages --cov-report=term-missing --cov-fail-under=55
```

To package already-generated v2 outputs without rerunning the pipeline:

```powershell
.\.venv\Scripts\python -m uk_wages.release_package
```

Launch the dashboard:

```powershell
.\.venv\Scripts\python -m streamlit run dashboard/app.py
```

## Files Worth Opening

- `dashboard/app.py` - Streamlit dashboard.
- `reports/research_note.md` - main written interpretation.
- `reports/policy_brief.md` - short summary only.
- `reports/methodology.md` - data choices and transformations.
- `docs/reviewer_guide.md` - suggested review path through the repo.
- `docs/v2_expansion_plan.md` - source-role guardrails for the triangulation upgrade.
- `config/sources.lock.yaml` - locked URLs, file hashes, release labels, download timestamps, and source file shapes for the release source set.
- `requirements.lock` - exact Python dependency constraints for the release environment.
- `releases/v2/evidence` - fixed reviewer package produced after a locked rebuild.
- `outputs/tables` - generated summary tables.
- `outputs/charts` - generated PNG charts.
- `outputs/evidence/source_value_checks.csv` - raw-to-processed spot checks.
- `outputs/evidence/final_claims.md` - qualified claim wording.
- `outputs/evidence/fragility_diagnostics.md` - why the 18-21 result is unstable.
- `outputs/evidence/triangulation_report.md` - age-preserving ASHE versus EARN01 direction and magnitude comparison.
- `outputs/evidence/rti_ashe_triangulation.md` - how RTI 18-24 compares with ASHE 18-21 and 22-29.
- `outputs/evidence/rti_ashe_annual_comparison.csv` - April-to-April RTI and ASHE annual overlap table.
- `outputs/evidence/ashe_decomposition_report.md` - hourly pay versus hours split and residual diagnostics.
- `outputs/tables/ashe_hours_decomposition_timeseries.csv` - year-by-year decomposition table.
- `outputs/evidence/ashe_quality_availability.md` - ASHE CV, quality, reliability, and suppression field audit.
- `outputs/evidence/ashe_uncertainty_bands.md` - approximate two-CV bands around 2019-to-latest ASHE changes.
- `outputs/evidence/option_b_ds_report.md` - structural-break relative weights, mixed-threshold minimum-wage event framing, and rough forecast-baseline diagnostics.
- `notebooks/option_b_walkthrough.ipynb` - notebook companion for Option B outputs.
- `outputs/evidence/ashe_composition_audit.md` - full-time, part-time, sex-split, hours, and job-count composition audit.
- `outputs/evidence/claim_confidence.md` - plain-English confidence labels for headline claims.
- `outputs/evidence/headline_number_lineage.csv` - source-to-claim map for headline numbers.
- `outputs/evidence/minimum_wage_context.md` - statutory wage-floor context.

Generated data and most outputs are ignored by git. Rebuild them with the commands above. The
reviewer-facing snapshot under `releases/v2/evidence` is committed for inspection without a
local rebuild.

Raw source files are not committed. `config/sources.lock.yaml` records the exact downloaded source files used for the release. `python -m uk_wages.download --locked` downloads only those locked URLs and verifies the recorded SHA256 hashes.

Some ONS lock entries still use mutable `/current/` aliases. That is an availability risk: an upstream replacement can return 404 or cause an exact hash mismatch. The locked pipeline fails closed in either case. Refreshing those entries requires a reviewed source-lock update; it never accepts changed bytes silently.

## Checks After Rebuild

- `pytest` should pass.
- `outputs/evidence/source_value_checks.csv` should show 17 passing checks.
- `outputs/evidence/manual_validation_audit.md` should include independent direct-cell checks for RTI and GOV.UK minimum wage rates.
- RTI Jan 2019 indices should equal 100 where data exist.
- `outputs/evidence/final_claims.md` should keep the 18-21 result qualified.
- `outputs/evidence/ashe_quality_availability.md` should state whether ASHE CV fields were available.
- `outputs/evidence/ashe_uncertainty_bands.md` should describe approximate two-CV bands without calling them confidence intervals.
- `outputs/evidence/triangulation_summary.csv` and `outputs/evidence/rti_ashe_annual_summary.csv` should contain directional concordance metrics.
- `outputs/evidence/option_b_ds_report.md` should keep the modelling caveats clear.
- `outputs/evidence/claim_confidence.md` should keep the clear 18-21 gain/loss claim marked as unsupported or qualified.
- `outputs/evidence/headline_number_lineage.csv` should map each headline number to source files and validation checks.
- `outputs/charts` should contain generated PNG charts.
- `reports/policy_brief.md` should not describe the ASHE result as a 2026 age-specific wage finding.

## Boundaries

ASHE is annual and age-specific. In the current source set, the latest ASHE age-specific wage year is 2025 provisional. The project title includes 2026 because MM23, RTI, A05 SA, EARN01, and minimum wage rates currently extend into 2026, but those sources do not provide 2026 age-specific ASHE wages.

RTI is PAYE administrative data. It covers payrolled employees, not self-employment or all income. It measures monthly pay, not ASHE weekly or hourly earnings. The latest RTI month is revision-prone.

This is descriptive analysis. It does not identify causal effects.

## CI

The default GitHub Actions workflow runs Ruff, mypy, and the test suite with the 55% coverage
floor on pushes and pull requests. The `Full pipeline evidence` workflow runs weekly and on
manual dispatch. It installs through `requirements.lock`, runs
`python -m uk_wages.pipeline --all --locked`, and uploads `releases/v2/evidence` as an artifact.
