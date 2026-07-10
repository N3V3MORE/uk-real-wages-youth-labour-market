# V2 Hardening Reconciliation Design

## Decision

Use `origin/main` at `1d5c7d1` as the v2 baseline. Preserve the local hardening commit
`2a04e59` by cherry-picking it onto `codex/reconcile-v2-hardening`, then resolve each
overlap according to the responsibilities below. Do not merge the stale local `main`
branch wholesale and do not force-push either branch.

This gives the project one line of history containing the v2 research work and the
release safeguards that were developed separately.

## Current State

The two branches carry complementary work:

- `origin/main` has the v2 and v3 analytical additions: a source lock, ASHE quality and
  composition audits, uncertainty bands, improved triangulation, Option B diagnostics,
  claim confidence, and headline-number lineage. Its baseline test result is 79 passed
  and 1 skipped.
- Local commit `2a04e59` has a dependency constraints file, lint/type/coverage gates, a
  locked evidence workflow, a release-package builder, and committed reviewer evidence.

The upstream branch removed most of those release safeguards while adding the new
analysis. The local branch never received the new analysis. The reconciliation must
retain both sets of capabilities without restoring obsolete v1 wording or file lists.

## Scope

The work has four deliverables:

1. Reconcile the local hardening commit with the v2 source tree.
2. Correct the fragility denominator and confidence-label bugs.
3. Publish a self-contained v2 reviewer evidence package with reproducibility metadata.
4. Restore automated lint, type, coverage, and locked full-pipeline checks.

The work does not change the research question, add data sources, strengthen causal
claims, or replace the existing source-lock format. Locked `/current/` source aliases
will be disclosed as an availability risk; they will not be rewritten without a stable
official historical URL.

## Integration Strategy

Cherry-pick `2a04e59` onto the v2 branch. Resolve conflicts with these rules:

- Keep the v2 module order and all v2 analytical modules.
- Keep `config/sources.lock.yaml` and make `--locked` continue to mean source locking.
- Port dependency constraints separately through `requirements.lock`; do not overload
  the `--locked` flag with a second meaning.
- Replace the v1 release file list with a v2 list. Do not restore deleted v1 output text.
- Restore quality configuration and workflows around the v2 code, then measure rather
  than assume the old thresholds still fit.
- Preserve upstream tests and add focused regressions for each corrected behavior.

If the cherry-pick produces a conflict whose intent is not covered here, prefer the v2
implementation and manually reapply the local safeguard as a separate change. This
keeps research behavior distinct from release operations.

## Correctness Changes

### Alternative-specification denominator

The baseline experiment is a reference, not an alternative specification. Add one
shared helper in `src/uk_wages/robustness.py` that removes rows whose
`experiment_name == "baseline"` before any fragility denominator is calculated.

Use that helper in:

- `compute_fragility_scores()`;
- `claims.assess_claims()` after baseline values have been obtained; and
- comparison-claim scoring after the baseline metric has been captured.

Do not automatically remove an alternative merely because its endpoint equals the
baseline. An unchanged sensitivity result can be genuine supporting evidence. The
separate issue that `exclude_2020` cannot alter a 2019-to-latest endpoint should remain
visible in diagnostics rather than being silently deduplicated.

For the current 18-21 core matrix, the expected count changes from three material
disagreements out of seven rows to three out of six alternatives. At the configured
threshold, 50% is `not robust`. Generated claims, confidence outputs, reports, and the
dashboard must all use the regenerated value.

### Confidence labels

Replace substring-based confidence inference with ordered, explicit verdict handling in
`src/uk_wages/claim_confidence.py`:

- `not robust` maps to `low confidence`, except the existing youngest-worker clear
  gain/loss claim remains `not supported`;
- `fragile` maps to `low confidence` unless the same youngest-worker rule applies;
- `moderately robust` and `robust` can map to `medium confidence` when quality evidence
  is not missing;
- non-ASHE contextual claims remain `descriptive only`.

The phrase `not robust` must never match the positive `robust` branch.

## V2 Evidence Package

Restore `src/uk_wages/release_package.py` as a release-operations module. It will build
`releases/v2/evidence` from a fixed reviewer-facing set:

- final qualified claims;
- the main research note;
- age-group real-earnings changes;
- fragility scores and diagnostics;
- source-value checks;
- ASHE quality availability and uncertainty bands;
- ASHE composition audit;
- RTI-ASHE and ASHE-EARN01 triangulation summaries;
- claim-confidence outputs;
- headline-number lineage outputs;
- Option B diagnostic report;
- `config/sources.lock.yaml`; and
- `requirements.lock`.

Raw workbooks, processed parquet files, and charts remain rebuild-only. The package
README must say this directly and point to the two lockfiles that define the source and
dependency environments.

The manifest records, for every packaged file, its original repo-relative path, package
name, byte size, and SHA-256 hash. It also records the SHA-256 hashes of the source and
dependency lockfiles. It must not contain a generation timestamp, absolute path, or
machine-specific value, so rebuilding unchanged inputs produces an unchanged package.

Package tests must verify that every declared file exists, every manifest hash matches,
the committed snapshot matches current generated outputs, and the README distinguishes
packaged evidence from rebuild-only lineage paths.

## Pipeline and Quality Gates

Keep Python 3.12 for the release environment. Restore the constraints-based installation:

```powershell
python -m pip install -r requirements.txt -c requirements.lock
python -m pip install -e . --no-deps
```

Restore these checks:

- `python -m ruff check`;
- `python -m mypy src` using the existing pragmatic pandas configuration as the starting
  baseline;
- `python -m pytest --cov=uk_wages --cov-report=term-missing --cov-fail-under=55`.

The initial coverage floor remains 55 because it is a preserved ratchet, not a claim
that 55 is sufficient. Raise it only if the reconciled v2 suite passes at a higher floor
without excluding production modules.

Extend the Makefile with `quality` and `release-evidence` targets. Make
`python -m uk_wages.pipeline --all --locked` run the v2 module sequence, pytest, and the
v2 release-package step. Keep the pipeline/Makefile order contract test.

CI on pushes and pull requests runs lint, type checking, and coverage. The full-pipeline
workflow runs weekly and by manual dispatch, installs through both lock inputs, executes
the source-locked pipeline, and uploads `releases/v2/evidence`. A clean unit-test checkout
may still skip raw-value integration, but the locked full-pipeline job must exercise it.

## Error Handling

- A missing alternative experiment produces an empty score rather than counting the
  baseline as evidence.
- A missing required package input fails with its repo-relative path.
- A source hash mismatch remains a hard failure in locked download mode.
- A manifest mismatch fails package validation instead of rewriting committed evidence
  during tests.
- Workflow artifact upload uses `if-no-files-found: error`.

## Test Strategy

Every behavior change follows red-green-refactor:

1. Add tests proving baseline rows are excluded from both fragility scores and claim
   assessments; observe the old seven-row count fail.
2. Add a confidence test where `verdict="not robust"`; observe the current medium label
   fail, then implement explicit verdict handling.
3. Add v2 package-contract tests before restoring the package builder.
4. Add workflow and pipeline contract tests before modifying CI or orchestration.
5. Run focused tests after each change, then the full unit suite, lint, mypy, coverage,
   package-integrity checks, and finally the locked full pipeline.

The final skeptical pass checks regenerated numeric counts, public wording, package
contents, source scope, and whether any ignored artifact is presented as committed.

## Acceptance Criteria

- The branch contains every upstream v2 commit plus the reconciled intent of `2a04e59`.
- The 18-21 core denominator counts six alternatives, not seven rows including baseline.
- `not robust` cannot produce `medium confidence`.
- A clean reviewer can inspect `releases/v2/evidence` without rebuilding raw data.
- The source and dependency environments are both locked and represented in the package.
- Push/PR CI enforces lint, type checking, and at least 55% coverage.
- The locked full-pipeline workflow rebuilds and uploads the v2 package.
- All tracked generated reports and committed evidence match their generators.
- The original divergent checkout remains unchanged.
