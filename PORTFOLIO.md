# UK Real Wages and Youth Labour Market Stress

Built a reproducible Python and Streamlit project analysing whether UK workers, especially younger workers, became better or worse off after inflation since 2019. The project uses official ASHE, CPIH/CPI, PAYE RTI, A05, EARN01, and GOV.UK minimum wage data, with locked sources, a deterministic pipeline, focused tests, a Streamlit dashboard, and evidence reports that separate what each source can and cannot prove.

The main finding is deliberately qualified: the headline 18-21 ASHE real weekly-earnings result is fragile and specification-dependent, while the 22-29 result is more stable. The project does not treat any one source as decisive; it triangulates ASHE against monthly PAYE RTI, whole-economy EARN01, labour-market stress indicators, minimum-wage context, and ASHE hourly-pay/hours decomposition.

## Analytical Signal

- Adds age-preserving ASHE-EARN01 and April-to-April RTI-ASHE concordance metrics instead of collapsing the core age signal.
- Uses published ASHE CV fields as approximate two-CV sensitivity bands around 2019-to-latest real earnings changes, without calling them confidence intervals.
- Decomposes ASHE weekly earnings into hourly pay, paid hours, and year-by-year residual diagnostics.
- Runs a YAML-driven robustness harness with fragility scores, contrarian findings, claim confidence labels, and source-value validation checks.
- Adds Option B data-science diagnostics: structural-break relative-weight screening, mixed-threshold minimum-wage event framing with descriptive DiD, and a simple forecast baseline with rough residual bands.

## Engineering Signal

- Reproducible data pipeline with `python -m uk_wages.pipeline --all`, source lockfiles, and generated evidence artifacts.
- Modular Python package for downloads, cleaning, analysis, robustness experiments, triangulation, evidence generation, and dashboard display.
- Tests cover source parsing, real-wage calculations, robustness logic, triangulation metrics, ASHE CV-band handling, Option B diagnostics, and pipeline/Makefile ordering.
- Written outputs include a research note, methodology, reviewer guide, final claims, evidence report, and dashboard-facing caveats.

## CV Version

Built a reproducible UK real-wages and youth labour-market dashboard using ASHE, CPIH/CPI, PAYE RTI, A05, EARN01, and minimum wage data. Added robustness diagnostics, source-value validation, approximate ASHE CV bands, ASHE-EARN01 and RTI-ASHE concordance metrics, hourly-pay/hours decomposition, structural-break screening, descriptive DiD event framing, and calibrated final claims showing that the 18-21 real-wage result is fragile and source-dependent.
