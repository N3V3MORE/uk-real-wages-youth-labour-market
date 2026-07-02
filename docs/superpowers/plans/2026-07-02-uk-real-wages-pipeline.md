# UK Real Wages Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible ONS-only Python research pipeline for UK real wages and youth labour-market stress since 2019.

**Architecture:** Keep raw acquisition, cleaning, analysis, charting, and dashboard display as separate command-line modules under `src/uk_wages`. The Streamlit app reads processed outputs only.

**Tech Stack:** Python, pandas, requests, BeautifulSoup, openpyxl, xlrd, pyarrow, matplotlib, Streamlit, pytest.

---

### Task 1: Repository Skeleton

**Files:** `README.md`, `AGENTS.md`, `pyproject.toml`, `requirements.txt`, `Makefile`, `config/sources.yaml`, `config/analysis.yaml`, directory placeholders.

- [ ] Create the documented project shape.
- [ ] Configure reproducible command-line targets.
- [ ] Keep ONS source URLs in config, not buried in notebooks.

### Task 2: Data Acquisition

**Files:** `src/uk_wages/download.py`, `src/uk_wages/utils.py`.

- [ ] Download CPIH and CPI time series from ONS MM23 generator CSV links.
- [ ] Download ASHE age and region-age editions from 2019 through latest configured ASHE edition.
- [ ] Download A05 SA and EARN01 current workbooks.
- [ ] Cache under `data/raw/<source>/<release>/` and write metadata JSON with URL, date, file name, and SHA256.

### Task 3: Cleaning

**Files:** `clean_cpi.py`, `clean_ashe.py`, `clean_region_ashe.py`, `clean_a05.py`, `clean_earn01.py`.

- [ ] Produce CPIH/CPI monthly and annual deflator parquet files.
- [ ] Produce ASHE national and region-age long-form parquet files.
- [ ] Produce A05 age labour-market rates, including a derived 16-24 aggregate.
- [ ] Produce monthly AWE real wage indices from EARN01.

### Task 4: Analysis and Outputs

**Files:** `analysis.py`, `charts.py`, `reports/methodology.md`, `reports/policy_brief.md`.

- [ ] Compute real earnings by age and region using CPIH, 2019 = 100.
- [ ] Save final CSV tables.
- [ ] Save required PNG and SVG charts with source and deflator notes.
- [ ] Keep the policy brief direct about the ASHE 2025 limit.

### Task 5: Dashboard and Verification

**Files:** `dashboard/app.py`, `tests/test_real_wage_calcs.py`, `tests/test_cleaning.py`.

- [ ] Create a Streamlit dashboard that reads processed parquet and CSV files only.
- [ ] Add compact tests for formula, baseline, required output fields, date parsing, and ASHE uniqueness.
- [ ] Run tests and the pipeline verification before claiming completion.

