# Methodology

## Sources

The pipeline uses official ONS/HMRC and GOV.UK sources:

- MM23 Consumer Price Inflation Time Series for CPIH and CPI.
- ASHE Table 6 for annual age-specific earnings.
- ASHE UK region by age group for annual regional age comparisons.
- PAYE RTI for monthly age-specific PAYE pay and payrolled employee counts.
- A05 SA for employment, unemployment, and inactivity by age.
- EARN01 for monthly average weekly earnings.
- GOV.UK National Minimum Wage and National Living Wage rates for statutory wage-floor context.

## Source Roles

| Source | What it is used for | Boundary |
| --- | --- | --- |
| ASHE Table 6 | Main annual age-specific earnings result. | The current ASHE age-specific wage run stops at 2025 provisional. |
| ASHE region by age | Annual regional age-specific earnings comparison. | It is not monthly evidence. |
| PAYE RTI | Monthly age-specific PAYE median pay and payrolled employment. | PAYE only; monthly pay; RTI 18-24 is not the same as ASHE 18-21. |
| ASHE hourly pay and hours | A descriptive weekly-pay split into hourly pay, hours, and residual movement. | A decomposition of medians, not a causal model. |
| ASHE CV and quality workbooks | Published coefficients of variation and quality markers where ASHE supplies them. | Quality evidence, not invented confidence intervals. |
| ASHE composition rows | Full-time, part-time, sex-split, paid-hours, and job-count checks where available. | Descriptive composition evidence, not causality. |
| GOV.UK minimum wage | Statutory wage-floor context by age threshold. | Age thresholds do not line up cleanly with ASHE age bands. |
| A05 SA | Youth employment, unemployment, and inactivity context. | Labour-market status, not earnings. |
| EARN01 | Monthly whole-economy and sector wage trend. | Not age-specific. |

## Deflating Pay

CPIH all-items is the default deflator. CPI all-items is kept as a sensitivity check.

ASHE is an annual earnings snapshot around April, so the main ASHE calculation uses April CPIH. The processed inflation table also keeps calendar-year average CPIH for sensitivity runs.

```text
real_wage_index = nominal_earnings_index / price_index * 100
```

The annual ASHE index uses 2019 = 100. The monthly EARN01 index uses January 2019 = 100.
The RTI real-pay index also uses January 2019 = 100.

## Earnings Measures

The main age comparison uses median weekly gross earnings for all employee jobs. Medians are less exposed to high-earner outliers than means. Mean weekly gross earnings are still cleaned and tested as a sensitivity measure.

The decomposition module also reads ASHE hourly gross pay, hourly pay excluding overtime, total paid hours, and basic paid hours when those workbooks are available. The report uses gross hourly pay and total paid hours for the headline split.

The robustness harness checks how the answer changes under alternative specifications. The ASHE quality module separately inspects ASHE age and region-by-age downloads for CV workbooks, confidence interval fields, standard errors, suppression markers, reliability markers, and quality notes. Where CV fields are present, the pipeline parses them as source quality markers. The analysis output also reports an approximate two-CV band around each 2019-to-latest ASHE real-earnings change by combining the baseline and latest published CVs. This is a rough sensitivity check, not a confidence interval, and it does not infer sampling error beyond the published CV fields.

The ASHE composition module checks whether the weekly result differs across all-employee, full-time, part-time, male, female, paid-hours, and published job-count rows where available. This helps separate composition evidence from wage evidence, but it is not a causal design.

## RTI Triangulation

The RTI age-pay module reads the seasonally adjusted ONS/HMRC reference table, using `28. Employees (Age)` and `29. Median pay (Age)`. It keeps monthly median PAYE pay and payrolled employee counts for Under 18, 18-24, 25-34, 35-49, 50-64, and 65+.

RTI is a check on whether monthly PAYE age data tells a similar or different story. It is not a replacement for ASHE because it covers PAYE employees, excludes self-employment income, and measures monthly pay rather than weekly or hourly earnings. The latest RTI month is flagged as revision-prone because the release describes it as an early estimate.

The RTI-ASHE triangulation report rebases April RTI observations to April 2019 and compares year-over-year directions with annual ASHE 18-21 and 22-29 rows where the years overlap. The age-band bridge remains imperfect: RTI 18-24 overlaps both ASHE groups, and RTI 25-34 still has no exact ASHE wage match in this pipeline.

## Option B Modelling Diagnostics

The Option B module adds three deterministic modelling diagnostics: a Bayesian-style discrete structural-break screen over ASHE real-earnings indices, a descriptive minimum-wage event-framing table comparing 18-21 with 22-29 around 2023-2025, and a simple linear-trend forecast baseline. These outputs are portfolio data-science evidence, not official forecasts or causal estimates.

## Minimum Wage Context

The minimum wage module parses GOV.UK rates from April 2019 onward and deflates statutory hourly rates with April CPIH. The adult threshold changes across the period: 25 and over before April 2021, 23 and over from April 2021 to March 2024, and 21 and over from April 2024.

Minimum wage bite is calculated only where ASHE hourly median pay is available. The mapping remains imperfect: ASHE 18-21 crosses the 18-20 and 21+ thresholds, and ASHE 22-29 mixes workers affected by different adult-rate histories.

## Frequency Limits

ASHE is annual and age-specific. RTI is monthly and age-specific for PAYE employees. EARN01 is monthly but not age-specific. A05 SA is rolling three-month labour-market data, not earnings data.

The 2026 part of the project title comes from current RTI, EARN01, inflation, A05 SA, and minimum-wage releases. ASHE age-specific wage statements should stop at the latest ASHE edition unless ASHE 2026 is added.

## A05 16-24 Derivation

The current A05 SA workbook publishes 16-17 and 18-24 separately. The pipeline derives 16-24 by summing employment, unemployment, activity, and inactivity levels for those two age bands, then recomputing rates from the combined levels.

The youth unemployment gap is derived 16-24 unemployment minus 25-34 unemployment. The youth inactivity gap is calculated the same way.
