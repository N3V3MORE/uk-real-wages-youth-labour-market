# Reviewer Guide

This guide is for someone checking whether the repo's conclusion is supported by the data and rebuild steps.

## Start Here

Read `reports/research_note.md` first. It is the main written interpretation. Use `reports/policy_brief.md` only as the short summary.

Then read `reports/methodology.md` for source roles and boundaries. ASHE supplies annual April age-group earnings through 2025 provisional. The saved June 2026 releases cover RTI through May (early estimate; April latest non-flash), A05 through February-April, and EARN01 through April. Minimum-wage rates extend to April 2026. These inputs describe a saved release rather than the latest October 2026 data.

The project updates an established research question. Review the linked Resolution Foundation, IFS, and ASHE representativeness research in the README and methodology. Prior studies are context, rather than an automatic numerical cross-check when periods, populations, source editions, or deflators differ.

## Rebuild Path

Create and install the constrained Python 3.12 environment from a fresh checkout:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -c requirements.lock
.\.venv\Scripts\python -m pip install --no-build-isolation --no-deps -e .
```

Reproduce the release against the committed source hashes:

```powershell
.\.venv\Scripts\python -m uk_wages.pipeline --all --locked
```

This command verifies or downloads the locked raw sources, rebuilds the analysis, creates the
reviewer package at `releases/v2/evidence`, and then runs the tests against the rebuilt package.
The default full pipeline and `make all` use locked inputs. On Windows, select the virtual
environment with `make PYTHON=./.venv/Scripts/python.exe all`.

Run the same quality gates enforced on pushes and pull requests:

```powershell
.\.venv\Scripts\python -m ruff check
.\.venv\Scripts\python -m mypy src
.\.venv\Scripts\python -m pytest --cov=uk_wages --cov-report=term-missing --cov-fail-under=55
```

After rebuild, check:

- `pytest` passes.
- `outputs/evidence/source_value_checks.csv` has 17 passing checks.
- `outputs/evidence/manual_validation_audit.md` includes direct-cell RTI checks and direct GOV.UK minimum-wage table checks.
- `outputs/evidence/claim_assessment.csv` marks the 18-21 result as not robust.
- `outputs/evidence/triangulation_summary.csv` keeps ASHE age groups separate when comparing with whole-economy EARN01.
- `outputs/evidence/rti_ashe_annual_summary.csv` reports April-to-April RTI-ASHE directional concordance for overlapping years.
- `outputs/evidence/ashe_decomposition_report.md` names 25-34 as unavailable for ASHE decomposition, rather than fabricating a row, and reports year-by-year residual diagnostics.
- `outputs/evidence/ashe_quality_availability.md` records which ASHE CV, quality, suppression, and reliability fields were checked.
- `outputs/evidence/ashe_uncertainty_bands.md` uses published CVs only as approximate two-CV sensitivity bands, not confidence intervals.
- `outputs/evidence/option_b_ds_report.md` adds structural-break relative weights, mixed-threshold event framing, and rough forecast-baseline diagnostics while keeping causal/forecast caveats.
- `outputs/evidence/ashe_composition_audit.md` separates work-status, sex-split, hours, and job-count composition evidence from wage evidence.
- `outputs/evidence/claim_confidence.md` gives each headline claim a plain-English confidence label.
- `outputs/evidence/headline_number_lineage.csv` maps headline numbers back to source files, processed files, modules, and validation checks.
- `config/sources.lock.yaml` records the locked source URLs, downloaded file paths, release labels, SHA256 hashes, download timestamps, and source file shapes used for release reproduction.

## CI Checks

The default CI workflow runs Ruff, mypy, and the full test suite with a 55% coverage floor on
pushes and pull requests. The `Full pipeline evidence` workflow runs weekly and by manual
dispatch. It uses Python 3.12, installs through `requirements.lock`, runs
`python -m uk_wages.pipeline --all --locked`, and uploads `releases/v2/evidence`; a missing
package fails the workflow rather than silently publishing an empty artifact.

The ONS lock uses dated ASHE editions and archived versions for CPI (`v129`), CPIH (`v130`),
A05 (`v124`), EARN01 (`v128`), and RTI (`v86`). Workbook URLs containing
`/current/previous/v.../` identify archived files, and the source hashes preserve the release data.

The GOV.UK minimum-wage Content API endpoint remains mutable. Its original 5 September 2026
JSON is bundled under `config/source_snapshots/<locked SHA256>.json`. Locked downloads restore
and verify this snapshot when the raw file is missing or `--force` is used. An October metadata
change therefore does not prevent reproduction or change the saved rates. Corrupt snapshots
and raw hash mismatches still fail verification. Sources without snapshots depend on publisher
availability. A maintainer must review and update the source lock before new bytes can enter
a release. A live-source refresh is separate from reproducing this package.

## Claims To Challenge

- Do not treat the 18-21 baseline loss as a clean finding. It changes under baseline-year, mean-vs-median, and full-time-only choices.
- Do not treat RTI 18-24 as the same population as ASHE 18-21.
- Do not treat minimum-wage rates as causal evidence. They are wage-floor context.
- Do not treat the project title's 2026 endpoint as ASHE 2026 age-specific wage evidence. The 2026 evidence comes from non-ASHE sources.
- Do not turn ASHE CV fields into confidence intervals. The project may use them for approximate two-CV sensitivity bands, but those bands are not source-supplied intervals.
- Do not treat Option B outputs as causal estimates, no-break posterior probabilities, or official forecasts. They are modelling diagnostics.
- Keep gross employee-job earnings separate from household living standards and changes for the same individuals. The project has no tax-benefit or household-cost calculation.
- Keep sampling precision separate from non-response and coverage bias. Passing source checks and a small CV do not establish representativeness.
- Distinguish sensitivity comparisons from statistical probabilities. Two endpoint-preserving stress specifications produce matching retained-age estimates by construction.
- Read composition pay changes as nominal and published job-count shares as proxies. They do not provide a composition-adjusted median.

## What Would Change The Conclusion?

A broader 18-21 earnings claim would become stronger if future source editions show a consistent pattern across explicitly comparable measures and the same sensitivity comparisons. The saved baseline's arithmetic can be checked directly even when other populations or start years give different results.

Poor source quality, revisions, or differing subgroup results could weaken that broader interpretation. Hourly pay can rise while weekly pay falls as hours and job mix change; that does not invalidate a measured weekly-earnings decline. RTI's wider age band and monthly concept require a separate interpretation.

The 22-29 claim would become stronger if quality flags remain reliable and robustness checks keep agreeing. It would weaken if source quality, work-status splits, or triangulation checks move away from the baseline ASHE result.

## Dashboard Check

Run:

```powershell
.\.venv\Scripts\python -m streamlit run dashboard/app.py
```

The dashboard should show the final claim wording, robustness tables, RTI triangulation, ASHE decomposition, ASHE quality and composition audits, minimum-wage context, labour-market stress, claim confidence, lineage, and source validation outputs.

Use **Download CSV** beneath a table to export its rows and all columns, including those
outside the horizontal viewport. This button keeps the original row order; sorting the table
does not sort the CSV. The labour-market stress export contains the 20 observations shown in
that table. The table toolbar also has a CSV control, whose native file picker depends on the
browser; the separate button uses the ordinary browser download flow.

## Verification On 5 October 2026

| Check | Evidence | Limit |
| --- | --- | --- |
| Rebuild from an empty checkout | A new clone started without raw data. Nineteen publisher files downloaded and the bundled GOV.UK snapshot restored; all 20 source hashes verified. All 18 packaged evidence files matched the committed release bytes, and 228 tests passed. | The mutable GOV.UK endpoint no longer serves the exact pinned metadata bytes. The preserved snapshot supplies them; a clean rebuild does not establish perpetual publisher availability. |
| Reproduce a published result | The Resolution Foundation November 2023 result for ages 18-21 was reproduced as -6.4088%, rounding to its published -6.4%. Years, provisional ASHE editions, all-sex/all-work-status median weekly gross pay, and April CPI were matched. The methodology shows the bridge to this release's -1.8087%. | The match is at published precision. The article does not provide its complete author calculation workflow. |
| Independent numerical audit | Separate calculations from raw ASHE workbooks, inflation CSVs and GOV.UK rate tables matched 28 break rows, 14 forecast rows and 10 numeric event-comparison fields: 192 comparisons, with a largest difference of about 1.84e-14 after output rounding. Break weights used RSS ratios; forecasts used closed-form least squares rather than the project model functions. | Seven annual observations remain a small sample. Conditional break weights, descriptive event comparisons and rough forecast bands do not establish a break, a causal effect or forecast accuracy. |
| Dashboard controls and charts | All nine tabs, 22 tables and nine dashboard chart images were checked at 1280x900 and 390x844. Every table and chart entered and exited fullscreen; every table reached its last column. Ascending and descending numeric sorting passed on desktop, and age-label sorting passed at the phone size. Actual ASHE and break-weight CSV downloads matched their source tables; all 22 export payloads matched the displayed datasets. All 13 generated PNG files matched the previously inspected charts byte for byte. | The mobile check uses a phone-sized browser viewport, not physical-device or touch-gesture testing. The separate Download CSV buttons are the verified export route. |
| Newer source editions | September RTI, A05 and EARN01 editions and current inflation series were compared with the pinned June editions. CPI and CPIH each matched all 461 overlapping months. Same-period revisions preserved the directions of the supporting comparisons; the ASHE 18-21 headline remains -1.81%. | Updated supporting sources have different age bands, earnings concepts and periods. They do not make the ASHE headline robust to its existing specification sensitivities. |

The original CSV gap is closed by the explicit download buttons. The checked desktop file
contained all seven ASHE rows and 15 columns; the phone-sized export contained all 28 break
rows and 12 columns. CSV payload checks also covered the renamed material-change columns and
the labour-market table's 20-row subset. The browser console reported no warnings or errors
after the final interaction checks.
