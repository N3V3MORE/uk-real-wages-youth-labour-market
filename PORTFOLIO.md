# UK Real Wages and Youth Labour Market Stress

This project asks whether gross weekly earnings for UK employee jobs in younger age groups kept up with inflation after 2019. It compares published age-group estimates across years, rather than following the same workers or measuring household living standards.

It uses official ASHE, CPIH/CPI, PAYE RTI, A05, EARN01, and GOV.UK minimum wage data. The pipeline downloads, cleans, checks, and rebuilds the saved release with `python -m uk_wages.pipeline --all --locked`. ASHE ends at April 2025 provisional. The June 2026 monthly releases cover RTI through May 2026 (early estimate, April latest non-flash), A05 through February-April 2026, and EARN01 through April 2026. Rates effective April 2026 provide minimum-wage context.

Baseline ASHE median weekly gross earnings for 18-21 fell 1.81% from April 2019 to April 2025 after April CPIH adjustment. The configured verdict is not robust: three of six core alternatives materially disagree. The 22-29 baseline gain is 3.57%, with one core disagreement. These counts summarise specified comparisons; they are not statistical confidence levels. Different start years and full-time-only rows answer different period or population questions.

This is a replication and update project. Earlier work by [Resolution Foundation](https://www.resolutionfoundation.org/comment/falling-pay-divergent-data-and-a-bulging-middle/) and [IFS](https://ifs.org.uk/sites/default/files/2024-05/What-has-happened-to-earnings-IFS-Report_0.pdf) covers the broad question and source disagreements. The portfolio contribution is the reproducible pipeline, documented assumptions, and inspectable evidence, rather than a claim of research novelty.

## What The Project Shows

- Age-preserving ASHE-EARN01 and April-to-April RTI-ASHE concordance metrics.
- Approximate two-CV bands from published ASHE CV fields, labelled as sensitivity checks rather than confidence intervals.
- A weekly-pay decomposition into hourly pay, paid hours, and residual movement.
- YAML-driven robustness experiments, fragility scores, contrarian findings, claim confidence labels, and source-value checks.
- Option B modelling diagnostics: structural-break relative weights, mixed-threshold minimum-wage event framing with descriptive DiD, and a simple forecast baseline with rough residual bands.

Separate medians and published job-count proxies do not identify how much composition caused earnings to change. Published CVs measure sampling precision and do not resolve survey coverage or non-response bias. The project makes no causal policy claim.

## Engineering Notes

- Source lockfiles and SHA checks make the official-data inputs auditable.
- The code is split into download, cleaning, analysis, triangulation, robustness, evidence, and dashboard modules.
- Tests cover parsing, real-wage calculations, source validation, robustness logic, triangulation metrics, CV-band handling, Option B diagnostics, and pipeline ordering.
- The written outputs include a research note, methodology, reviewer guide, final claims, evidence report, and Streamlit dashboard.

## CV Version

Built a reproducible UK real-earnings pipeline and dashboard from official sources, with locked inputs, source-value checks, sensitivity comparisons, and explicit sampling and population caveats. The saved 2019-2025 ASHE median weekly comparison is -1.81% for ages 18-21 and +3.57% for ages 22-29; the youngest group's conclusion changes with the comparison chosen.
