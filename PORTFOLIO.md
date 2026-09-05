# UK Real Wages and Youth Labour Market Stress

This project asks a narrow question: did UK workers, especially younger workers, keep up with inflation after 2019?

It uses official ASHE, CPIH/CPI, PAYE RTI, A05, EARN01, and GOV.UK minimum wage data. The pipeline downloads, cleans, checks, and rebuilds the evidence with `python -m uk_wages.pipeline --all`.

The headline result is cautious. Baseline ASHE says 18-21 real weekly earnings fell slightly from 2019 to 2025, but the configured verdict is not robust: three of six core alternatives materially disagree. The 22-29 result is steadier. RTI, EARN01, A05, minimum wage rates, and ASHE hours data are used as checks, not substitutes for ASHE.

## What The Project Shows

- Age-preserving ASHE-EARN01 and April-to-April RTI-ASHE concordance metrics.
- Approximate two-CV bands from published ASHE CV fields, labelled as sensitivity checks rather than confidence intervals.
- A weekly-pay decomposition into hourly pay, paid hours, and residual movement.
- YAML-driven robustness experiments, fragility scores, contrarian findings, claim confidence labels, and source-value checks.
- Option B modelling diagnostics: structural-break relative weights, mixed-threshold minimum-wage event framing with descriptive DiD, and a simple forecast baseline with rough residual bands.

## Engineering Notes

- Source lockfiles and SHA checks make the official-data inputs auditable.
- The code is split into download, cleaning, analysis, triangulation, robustness, evidence, and dashboard modules.
- Tests cover parsing, real-wage calculations, source validation, robustness logic, triangulation metrics, CV-band handling, Option B diagnostics, and pipeline ordering.
- The written outputs include a research note, methodology, reviewer guide, final claims, evidence report, and Streamlit dashboard.

## CV Version

Reproducible UK real-wages dashboard using ASHE, CPIH/CPI, PAYE RTI, A05, EARN01, and minimum wage data, with source validation, robustness experiments, approximate ASHE CV bands, ASHE-EARN01 and RTI-ASHE concordance metrics, hourly-pay/hours decomposition, structural-break screening, descriptive DiD event framing, and calibrated final claims showing that the configured 18-21 verdict is not robust and the result is source-dependent.
