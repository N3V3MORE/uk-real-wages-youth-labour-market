# V2 Hardening Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Combine the upstream v2 analytical work with the local release safeguards, correct the research-scoring bugs, and publish a verified v2 evidence package to `main`.

**Architecture:** Start from `origin/main`, preserve the intent of local commit `2a04e59` through a deliberate cherry-pick, and keep research logic separate from release operations. A shared alternative-row filter feeds fragility and claim scoring; a dedicated release-package module copies a fixed reviewer bundle and produces a deterministic manifest; CI and the full-pipeline workflow enforce the two lock inputs and the restored quality gates.

**Tech Stack:** Python 3.12, pandas, pytest, pytest-cov, Ruff, mypy, GitHub Actions, YAML, Markdown.

## Global Constraints

- Keep every analytical module present at `origin/main` commit `1d5c7d1`.
- Preserve the release-hardening intent of local commit `2a04e59`; do not restore obsolete v1 wording or overwrite v2 generators with older code.
- `--locked` means `config/sources.lock.yaml`; dependency constraints remain a separate `requirements.lock` input.
- The baseline experiment is never counted as an alternative specification.
- An unchanged alternative remains valid supporting evidence; do not deduplicate alternatives by outcome value.
- `not robust` maps to `low confidence`, except the youngest-worker clear gain/loss claim remains `not supported`.
- Build committed reviewer evidence under `releases/v2/evidence`; raw workbooks, processed parquet files, and charts remain rebuild-only.
- Use Python 3.12 for release checks and retain a coverage floor of at least 55%.
- Do not add data sources or strengthen causal claims.
- Follow red-green-refactor for every behavior change.
- For local Windows commands, use `C:\Users\Sushmit\Desktop\Code\proj\.venv\Scripts\python.exe` as the `python` executable; CI snippets continue to use `python`.

---

### Task 1: Reconcile the local hardening commit onto v2

**Files:**
- Merge source: commit `2a04e59`
- Preserve from v2: `src/uk_wages/*.py`, `tests/*.py`, `reports/*.md`, `config/sources.lock.yaml`, `notebooks/option_b_walkthrough.ipynb`
- Restore for later tasks: `requirements.lock`, `src/uk_wages/release_package.py`, `.github/workflows/pipeline-evidence.yml`

**Interfaces:**
- Consumes: v2 branch at design commit `bbdc448`; local hardening commit `2a04e59`.
- Produces: one reconciled Git state in which v2 behavior is intact and the local release files are available for adaptation.

- [ ] **Step 1: Record the pre-reconciliation state**

Run:

```powershell
git status --short --branch
git rev-parse HEAD
git show --stat --oneline 2a04e59
```

Expected: clean branch `codex/reconcile-v2-hardening`; HEAD includes the design commit; `2a04e59` resolves.

- [ ] **Step 2: Cherry-pick the hardening commit**

Run:

```powershell
git cherry-pick 2a04e59
```

Expected: conflicts because v2 changed many of the same files.

- [ ] **Step 3: Resolve conflicts by responsibility**

Use the `resolving-merge-conflicts` skill. For research modules, tests, reports, README, dashboard, and source configuration, begin from the v2 side and reapply only release-operational changes. Preserve the incoming versions of `requirements.lock` and `src/uk_wages/release_package.py` so later tasks can adapt them. Keep `config/sources.lock.yaml`, all v2 tests, v2 analytical modules, and `notebooks/option_b_walkthrough.ipynb` from HEAD. Old v1 contract tests are source material for later test-first tasks, not files to restore during reconciliation.

Run after editing:

```powershell
git diff --name-only --diff-filter=U
git diff --check
git add --all
git cherry-pick --continue
```

Expected: no unmerged paths; cherry-pick completes without a second merge commit.

- [ ] **Step 4: Verify v2 behavior survived reconciliation**

Run:

```powershell
python -m pytest
```

Expected: the v2 suite passes; release-operation tests may be collected only if their restored imports resolve.

- [ ] **Step 5: Commit any post-cherry-pick normalization**

If conflict resolution required changes after `cherry-pick --continue`, stage only those files and run:

```powershell
git commit -m "chore: reconcile v2 with release hardening"
```

Expected: working tree clean and v2 files retained.

---

### Task 2: Correct alternative counts and confidence classification

**Files:**
- Modify: `src/uk_wages/robustness.py`
- Modify: `src/uk_wages/claims.py`
- Modify: `src/uk_wages/claim_confidence.py`
- Modify: `src/uk_wages/fragility_diagnostics.py`
- Modify: `tests/test_fragility_diagnostics.py`
- Modify: `tests/test_experiment_harness.py`
- Modify: `tests/test_claim_confidence_and_lineage.py`

**Interfaces:**
- Produces: `alternative_specifications(rows: pd.DataFrame) -> pd.DataFrame` in `uk_wages.fragility_diagnostics`.
- Consumers: `compute_fragility_scores()` and `claims.assess_claims()`.

- [ ] **Step 1: Write failing denominator tests**

Add tests that include one `baseline` row plus six core alternatives and assert:

```python
core = scores.loc[scores["spec_tier"].eq("core")].iloc[0]
assert core["specifications_tested"] == 6
assert core["material_disagreements"] == 3
assert core["fragility_score"] == 0.5
assert core["assessment"] == "not robust"
```

Add a claim-assessment test using the same matrix and assert `specifications_tested == 6` and `verdict == "not robust"`.

- [ ] **Step 2: Run the denominator tests and verify RED**

Run:

```powershell
python -m pytest tests/test_fragility_diagnostics.py tests/test_experiment_harness.py -q
```

Expected: failures show seven rows counted instead of six and a `fragile` verdict instead of `not robust`.

- [ ] **Step 3: Implement the shared alternative filter**

Add to `fragility_diagnostics.py`:

```python
def alternative_specifications(rows: pd.DataFrame) -> pd.DataFrame:
    if "experiment_name" not in rows.columns:
        return rows.copy()
    return rows.loc[~rows["experiment_name"].eq("baseline")].copy()
```

Import it into `robustness.py` and call it inside `compute_fragility_scores()` before `total`, `disagree`, and `material` are calculated. Import and call it in `claims.assess_claims()` after comparison baselines and tier filters have been resolved but before claim totals are calculated.

- [ ] **Step 4: Run denominator tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_fragility_diagnostics.py tests/test_experiment_harness.py -q
```

Expected: all focused denominator and claim tests pass.

- [ ] **Step 5: Write the failing confidence test**

Add a public test through `build_claim_confidence()` with:

```python
{
    "claim_id": "c2_22_29_real_wages",
    "verdict": "not robust",
    "recommended_wording": "Treat this result as specification-sensitive.",
}
```

Assert that the generated `confidence_label` is `low confidence`, not `medium confidence`.

- [ ] **Step 6: Run confidence test and verify RED**

Run:

```powershell
python -m pytest tests/test_claim_confidence_and_lineage.py -q
```

Expected: current substring logic returns `medium confidence`.

- [ ] **Step 7: Replace substring inference with explicit verdict handling**

Refactor `_confidence_label()` so it normalises `verdict` separately and applies this order:

```python
if "youngest" in claim_id and verdict_key in {"fragile", "not robust"}:
    return "not supported"
if any(token in claim_id for token in ["rti", "hourly", "hours", "minimum_wage"]):
    return "descriptive only"
if verdict_key in {"fragile", "not robust"}:
    return "low confidence"
if "missing" in quality.lower() or "unavailable" in quality.lower():
    return "low confidence"
if verdict_key in {"moderately robust", "robust"}:
    return "medium confidence"
return "descriptive only"
```

- [ ] **Step 8: Run focused and full tests**

Run:

```powershell
python -m pytest tests/test_claim_confidence_and_lineage.py tests/test_fragility_diagnostics.py tests/test_experiment_harness.py -q
python -m pytest
```

Expected: focused tests and full suite pass.

- [ ] **Step 9: Commit**

```powershell
git add src/uk_wages/fragility_diagnostics.py src/uk_wages/robustness.py src/uk_wages/claims.py src/uk_wages/claim_confidence.py tests/test_fragility_diagnostics.py tests/test_experiment_harness.py tests/test_claim_confidence_and_lineage.py
git commit -m "fix: count only alternative robustness specifications"
```

---

### Task 3: Build a deterministic v2 evidence package

**Files:**
- Modify: `src/uk_wages/release_package.py`
- Create: `tests/test_release_packaging.py`
- Create: `releases/v2/evidence/*` through the generator

**Interfaces:**
- Produces: `build_release_package(project_root: str | Path = project_path(), release_name: str = "v2") -> Path`.
- Consumes: fixed `ReleaseFile` declarations and both lockfiles.

- [ ] **Step 1: Write failing package-contract tests**

Declare the expected flat package names:

```python
EXPECTED_V2_FILES = {
    "final_claims.md",
    "research_note.md",
    "age_group_real_earnings_change.csv",
    "fragility_scores.csv",
    "fragility_diagnostics.md",
    "source_value_checks.csv",
    "ashe_quality_availability.md",
    "ashe_uncertainty_bands.md",
    "ashe_composition_audit.md",
    "triangulation_summary.csv",
    "rti_ashe_annual_summary.csv",
    "claim_confidence_ladder.csv",
    "claim_confidence.md",
    "headline_number_lineage.csv",
    "headline_number_lineage.md",
    "option_b_ds_report.md",
    "sources.lock.yaml",
    "requirements.lock",
}
```

Assert the manifest has the same file set, every hash has 64 characters, `source_lock_sha256` and `requirements_lock_sha256` equal the packaged lockfile hashes, and the README contains both `packaged evidence` and `rebuild-only`.

- [ ] **Step 2: Run package tests and verify RED**

Run:

```powershell
python -m pytest tests/test_release_packaging.py -q
```

Expected: the restored v1 file list and default release name fail the v2 contract.

- [ ] **Step 3: Implement the v2 fixed file list**

Replace `REQUIRED_RELEASE_FILES` with `V2_RELEASE_FILES` containing the repo-relative sources listed in the design spec and the exact flat names in `EXPECTED_V2_FILES`. Set the default release name to `v2`.

Build the manifest as:

```python
{
    "release_name": release_name,
    "source_lock_sha256": sha256_file(package_root / "sources.lock.yaml"),
    "requirements_lock_sha256": sha256_file(package_root / "requirements.lock"),
    "files": manifest_files,
}
```

Keep it deterministic: no absolute paths, timestamps, hostnames, or environment dumps.

- [ ] **Step 4: Make package README boundaries explicit**

Generate README wording that says the folder is `packaged evidence`, raw/processed/chart paths in lineage are `rebuild-only`, `sources.lock.yaml` fixes source bytes, and `requirements.lock` constrains Python dependencies.

- [ ] **Step 5: Run package tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_release_packaging.py -q
```

Expected: all package-contract tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/uk_wages/release_package.py tests/test_release_packaging.py
git commit -m "feat: package v2 reviewer evidence"
```

---

### Task 4: Restore dependency and quality gates on v2

**Files:**
- Modify: `requirements.txt`
- Modify: `requirements.lock`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/test_quality_gates.py`

**Interfaces:**
- Produces: reproducible Python 3.12 install and executable `quality` gate commands.
- Consumes: current v2 runtime dependency set.

- [ ] **Step 1: Write failing quality-contract tests**

Assert that CI installs with both `requirements.txt` and `requirements.lock`, runs Ruff, mypy, and pytest coverage, and enforces `--cov-fail-under=55`. Assert `pyproject.toml` configures Ruff, mypy, branch coverage, and `fail_under = 55`.

- [ ] **Step 2: Run quality-contract tests and verify RED**

Run:

```powershell
python -m pytest tests/test_quality_gates.py -q
```

Expected: upstream CI lacks all three quality commands and the pyproject configuration.

- [ ] **Step 3: Restore dev dependencies and constraints install**

Ensure `requirements.txt` includes `coverage[toml]`, `mypy`, `pandas-stubs`, `pytest`, `pytest-cov`, `ruff`, `types-PyYAML`, and `types-requests`. Retain exact compatible pins in `requirements.lock` and keep the documented install command:

```powershell
python -m pip install -r requirements.txt -c requirements.lock
```

- [ ] **Step 4: Restore pragmatic quality configuration**

Restore the local commit's coverage, Ruff, and mypy sections. Keep Ruff correctness rules `E9` and `F`, Python 3.12 mypy, `check_untyped_defs = true`, and the existing pandas-noise error-code exclusions. Do not exclude an entire v2 module.

- [ ] **Step 5: Update CI and make the contract green**

Use Python 3.12, install from both requirement files, and run:

```yaml
- name: Lint
  run: python -m ruff check
- name: Type check
  run: python -m mypy src
- name: Tests with coverage
  run: python -m pytest --cov=uk_wages --cov-report=term-missing --cov-fail-under=55
```

Run:

```powershell
python -m pytest tests/test_quality_gates.py -q
python -m ruff check
python -m mypy src
python -m pytest --cov=uk_wages --cov-report=term-missing --cov-fail-under=55
```

Expected: contract tests pass, Ruff and mypy have zero errors, full suite passes above 55% coverage.

- [ ] **Step 6: Commit**

```powershell
git add requirements.txt requirements.lock pyproject.toml .github/workflows/ci.yml tests/test_quality_gates.py
git commit -m "ci: restore v2 quality gates"
```

---

### Task 5: Wire locked pipeline packaging and artifact CI

**Files:**
- Modify: `src/uk_wages/pipeline.py`
- Modify: `Makefile`
- Modify: `.github/workflows/full_pipeline.yml`
- Remove: `.github/workflows/pipeline-evidence.yml`
- Modify: `tests/test_pipeline.py`
- Create: `tests/test_release_operations.py`
- Modify: `README.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `python -m uk_wages.pipeline --all --locked` that finishes by packaging v2 evidence.
- Produces: one full-pipeline workflow with weekly and manual triggers and artifact upload.

- [ ] **Step 1: Write failing orchestration tests**

Assert that:

```python
assert PIPELINE_MODULES[-2:] == ["pytest", "uk_wages.release_package"]
```

Assert Makefile `all` includes `release-evidence`, and the full-pipeline workflow contains `schedule:`, `workflow_dispatch:`, `python -m uk_wages.pipeline --all --locked`, `actions/upload-artifact@v4`, and `releases/v2/evidence`.

- [ ] **Step 2: Run orchestration tests and verify RED**

Run:

```powershell
python -m pytest tests/test_pipeline.py tests/test_release_operations.py -q
```

Expected: release packaging and locked artifact workflow assertions fail.

- [ ] **Step 3: Extend pipeline and Makefile**

Append `uk_wages.release_package` after `pytest` in `PIPELINE_MODULES`. Add:

```make
quality: lint typecheck coverage

release-evidence:
	$(PYTHON) -m uk_wages.release_package

all: data clean analysis charts evidence test release-evidence
```

Add matching `lint`, `typecheck`, and `coverage` targets and `.PHONY` names.

- [ ] **Step 4: Consolidate full-pipeline workflow**

Keep `.github/workflows/full_pipeline.yml` as the single workflow. Use Python 3.12, constraints installation, weekly schedule plus manual dispatch, run the locked pipeline, and upload `releases/v2/evidence` with `if-no-files-found: error`. Remove the duplicate workflow with `git rm .github/workflows/pipeline-evidence.yml`.

- [ ] **Step 5: Align public metadata and commands**

Set project version to `2.0.0`, change the package description to `Reproducible analysis of UK real wages and youth labour market stress using official UK public sources since 2019.`, and document locked rebuild, quality, and v2 evidence paths in README.

- [ ] **Step 6: Run orchestration tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_pipeline.py tests/test_release_operations.py -q
python -m pytest
```

Expected: orchestration tests and full suite pass.

- [ ] **Step 7: Commit**

```powershell
git add src/uk_wages/pipeline.py Makefile .github/workflows/full_pipeline.yml tests/test_pipeline.py tests/test_release_operations.py README.md pyproject.toml
git commit -m "ci: publish locked v2 evidence pipeline"
```

---

### Task 6: Rebuild evidence and verify the release candidate

**Files:**
- Regenerate: `reports/research_note.md`
- Regenerate: `reports/policy_brief.md`
- Generate and commit: `releases/v2/evidence/*`
- Modify generator sources only if regenerated wording exposes a contradiction

**Interfaces:**
- Consumes: reconciled pipeline, both lockfiles, corrected scoring.
- Produces: reviewer-visible v2 evidence matching generator outputs.

- [ ] **Step 1: Run the complete locked pipeline**

Run:

```powershell
python -m uk_wages.pipeline --all --locked
```

Expected: locked hashes verify, every module runs, pytest passes, and `releases/v2/evidence` is generated.

- [ ] **Step 2: Verify corrected published results**

Check generated CSV/Markdown and assert:

```text
18-21 core specifications tested: 6
18-21 core material disagreements: 3
18-21 core verdict: not robust
18-21 clear gain/loss confidence: not supported
```

Confirm source-scope wording still distinguishes ASHE, RTI, A05, EARN01, HMRC, and GOV.UK roles.

- [ ] **Step 3: Verify package integrity independently**

Run a script or test that recomputes SHA-256 for each manifest entry and compares each packaged file with its declared source. Every manifest entry must match and no absolute path may appear.

- [ ] **Step 4: Run all release gates fresh**

Run:

```powershell
python -m ruff check
python -m mypy src
python -m pytest --cov=uk_wages --cov-report=term-missing --cov-fail-under=55
git diff --check
git status --short
```

Expected: zero lint/type/test/diff errors; only intended regenerated and package files are modified before commit.

- [ ] **Step 5: Commit generated evidence**

```powershell
git add reports releases/v2/evidence
git commit -m "docs: publish reconciled v2 evidence"
```

- [ ] **Step 6: Final branch verification**

Run the complete gate sequence again from the committed tree and confirm `git status --short` is empty.
