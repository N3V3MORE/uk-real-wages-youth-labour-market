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

The committed source lock preserves ASHE through April 2025 provisional and June 2026 monthly releases: RTI through May 2026 (early estimate; April is the latest non-flash month), A05 through February-April 2026, and EARN01 through April 2026. Minimum-wage rates extend to those effective April 2026. These are saved editions, not a live feed of the latest releases. Source updates require a separate review and lockfile change.

## Source Roles

| Source | What it is used for | Boundary |
| --- | --- | --- |
| ASHE Table 6 | Main annual age-specific earnings result. | The saved ASHE age-specific wage run stops at 2025 provisional. |
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

The main age comparison uses median weekly gross earnings from the published all-sex, all-work-status employee-job rows in ASHE Table 6. ASHE samples jobs around an April reference period; the weekly figure is not annual income. Successive age-group estimates describe different groups of jobs and people, rather than an individual-worker or birth-cohort trajectory. Medians are less exposed to high-earner outliers than means. Mean weekly gross earnings are still cleaned and tested as a sensitivity measure.

Gross earnings are before deductions. This analysis does not combine taxes, benefits, other household income, housing costs, or self-employment income into a living-standards measure. CPIH and CPI describe aggregate prices; neither supplies a personal or age-specific inflation rate here.

The decomposition module also reads ASHE hourly gross pay, hourly pay excluding overtime, total paid hours, and basic paid hours when those workbooks are available. The report uses gross hourly pay and total paid hours for the headline split.

The robustness harness checks how the answer changes under alternative specifications. The ASHE quality module separately inspects ASHE age and region-by-age downloads for CV workbooks, confidence interval fields, standard errors, suppression markers, reliability markers, and quality notes. Where CV fields are present, the pipeline parses them as source quality markers. The analysis output also reports an approximate two-CV band around each 2019-to-latest ASHE real-earnings change by combining the baseline and latest published CVs. This is a rough sensitivity check, not a confidence interval, and it does not infer sampling error beyond the published CV fields.

The approximate two-CV margin in percentage points is `2 * (1 + real_change / 100) * sqrt(baseline_cv^2 + latest_cv^2)`. This treats the deflator as fixed and assumes independent baseline and latest sampling errors because cross-year covariance is unavailable. It remains a sensitivity band, not a confidence interval.

CVs describe sampling precision, not the absence of coverage or non-response bias. [Forth and colleagues](https://openaccess.city.ac.uk/id/eprint/35689/) (online 2025; 2026 issue) document underrepresentation after official weighting. The pipeline checks published values and transformations; it does not reweight microdata or quantify that bias for its age-specific estimates. Confidence labels in the evidence files are rule-based assessments, not estimated probabilities.

The six core alternatives are configured comparisons rather than independent trials. A 2020 or 2021 baseline measures a different interval; a mean describes a different statistic; a full-time-only stress test covers different jobs. The stress specifications excluding 2020 from the path or restricting displayed age groups keep the baseline and latest endpoint values for retained groups, so matching endpoint results are expected. Materiality uses the configured one-percentage-point threshold; a material magnitude difference need not reverse the sign.

The ASHE composition module compares nominal weekly pay across all-employee, full-time, part-time, male, and female rows, alongside paid hours and published job counts. Job-count ratios are descriptive composition proxies. Subgroup medians cannot be averaged with these ratios to reconstruct or standardise the all-employee median. This module does not estimate a composition-adjusted wage change or a causal effect.

## RTI Triangulation

The RTI age-pay module reads the seasonally adjusted ONS/HMRC reference table, using `28. Employees (Age)` and `29. Median pay (Age)`. It keeps monthly median PAYE pay and payrolled employee counts for Under 18, 18-24, 25-34, 35-49, 50-64, and 65+.

RTI is a check on whether monthly PAYE age data tells a similar or different story. It is not a replacement for ASHE because it covers PAYE employees, excludes self-employment income, and measures monthly pay rather than weekly or hourly earnings. The latest RTI month is flagged as revision-prone because the release describes it as an early estimate.

The RTI-ASHE triangulation report rebases April RTI observations to April 2019 and compares year-over-year directions with annual ASHE 18-21 and 22-29 rows where the years overlap. The age-band bridge remains imperfect: RTI 18-24 overlaps both ASHE groups, and RTI 25-34 still has no exact ASHE wage match in this pipeline.

## Option B Modelling Diagnostics

The Option B module adds three deterministic modelling diagnostics: a discrete structural-break relative-weight screen over ASHE real-earnings indices, a descriptive minimum-wage event-framing table comparing 18-21 with 22-29 around 2023-2025 while showing both 18-to-20 and adult-threshold wage-floor context, and a simple linear-trend forecast baseline with rough residual bands. These outputs are modelling context, not official forecasts or causal estimates.

## Minimum Wage Context

The minimum wage module parses GOV.UK rates from April 2019 onward and deflates statutory hourly rates with April CPIH. The adult threshold changes across the period: 25 and over before April 2021, 23 and over from April 2021 to March 2024, and 21 and over from April 2024.

Minimum wage bite is calculated only where ASHE hourly median pay is available. The mapping remains imperfect: ASHE 18-21 crosses the 18-20 and 21+ thresholds, and ASHE 22-29 mixes workers affected by different adult-rate histories.

## Frequency Limits

ASHE is annual and age-specific. RTI is monthly and age-specific for PAYE employees. EARN01 is monthly but not age-specific. A05 SA is rolling three-month labour-market data, not earnings data.

The 2026 part of the project title comes from the saved monthly and minimum-wage sources. ASHE age-specific wage statements stop at 2025 provisional in this release.

## A05 16-24 Derivation

The saved A05 SA workbook publishes 16-17 and 18-24 separately. The pipeline derives 16-24 by summing employment, unemployment, activity, and inactivity levels for those two age bands, then recomputing rates from the combined levels.

The youth unemployment gap is derived 16-24 unemployment minus 25-34 unemployment. The youth inactivity gap is calculated the same way.

Gap changes compare the latest rolling three-month period with the mean of the rolling periods ending in 2019. The latest saved period is February-April 2026, represented by its end date, 30 April 2026. A gap change is not the youth group's own rate change. Unemployment rates use economically active people as the denominator; inactivity rates use the age-group population. A05 is official statistics in development and supplies contextual evidence for a broader age group than ASHE 18-21.

## Relationship To Earlier Research

This is a replication and update exercise. [Resolution Foundation's November 2023 analysis](https://www.resolutionfoundation.org/comment/falling-pay-divergent-data-and-a-bulging-middle/) examines age-specific real weekly pay since 2019; its [December 2023 youth report](https://www.resolutionfoundation.org/publications/narrowing-the-youth-gap/) discusses hourly pay and hours. [Henry and Joyce (IFS, May 2024)](https://ifs.org.uk/sites/default/files/2024-05/What-has-happened-to-earnings-IFS-Report_0.pdf) compare earnings sources. Before comparing their numbers with this release, align the period, source edition, earnings statistic, population, and deflator. The pipeline's contribution is reproducibility and explicit sensitivity testing; it makes no claim that the broad research question is new.

On 5 October 2026, a direct workbook calculation reproduced the November article's 18-21 median weekly real-pay change at its published one-decimal precision. The [2019 provisional Table 6](https://www.ons.gov.uk/file?uri=/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/agegroupashetable6/2019provisional/table62019provisional.zip) gives GBP 238.4. The [original 2023 provisional Table 6](https://www.ons.gov.uk/file?uri=/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/agegroupashetable6/2023provisional/previous/v1/ashetable62023provisional.zip), available when the article appeared on 2 November, gives GBP 270.4. The correction published the following day leaves that pay level unchanged. April CPI values of 107.6 and 130.4 give `100 * ((270.4 / 238.4) * (107.6 / 130.4) - 1) = -6.4088%`, rounding to the published -6.4%. The [article's chart](https://www.resolutionfoundation.org/app/uploads/2023/11/groups.png) identifies CPI adjustment. Matching the provisional editions reproduces the number; the article does not expose its complete calculation workflow.

The following calculations keep the all-sex, all-work-status median weekly gross-pay rows and April price indices. They explain how editions, deflators, and endpoints change the result:

| ASHE editions and period | Deflator | 18-21 real change |
| --- | --- | --- |
| 2019 and 2023 provisional | CPI | -6.4088% |
| 2019 revised; 2023 provisional | CPI | -6.6047% |
| 2019 and 2023 revised | CPI | -5.2231% |
| 2019 and 2023 revised | CPIH | -3.6718% |
| 2019 revised; 2025 provisional, saved release | CPIH | -1.8087% |

## Checks Against Newer Source Editions

The 5 October check rebuilt the saved release from an initially empty raw cache. All 20 source hashes verified and all 18 packaged evidence inputs matched the prior release. The mutable GOV.UK endpoint had changed only its timestamp and links. Its exact 5 September JSON is now bundled under `config/source_snapshots`; the source lock and rates are unchanged. Independent arithmetic from the raw workbooks also matched all 28 structural-break rows, 14 forecast rows, and 10 numeric event-comparison fields. Those checks validate the calculations, not the models' causal interpretation or forecast accuracy.

The September 2026 monthly editions were downloaded separately to compare revisions without replacing the release. The current [ASHE Table 6 page](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/agegroupashetable6) still lists 2025 provisional as its newest edition. CPI and CPIH each matched all 461 overlapping monthly values, including April 2019 and April 2025, so the saved ASHE headline remains -1.81%.

| Supporting measure, same endpoint | Saved June edition | September edition |
| --- | --- | --- |
| RTI 18-24 real monthly pay, Jan 2019-May 2026 change | +6.22% | +6.92% |
| RTI 18-24 employee count, Jan 2019-May 2026 change | -2.86% | -2.80% |
| A05 youth unemployment gap change, Feb-Apr 2026 vs mean periods ending in 2019 | +3.70pp | +3.67pp |
| A05 youth inactivity gap change, same periods | +2.68pp | +2.77pp |
| EARN01 whole-economy real regular pay, Apr 2026, Jan 2019=100 | 105.05 | 105.05 |
| EARN01 whole-economy real total pay, same month and base | 106.68 | 106.63 |

Sources: September editions of [RTI](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/realtimeinformationstatisticsreferencetableseasonallyadjusted/current), [A05](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/datasets/employmentunemploymentandeconomicinactivitybyagegroupseasonallyadjusteda05sa/current), and [EARN01](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/datasets/averageweeklyearningsearn01), with current [CPIH](https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/l522/mm23). The revised RTI May estimate is no longer the latest flash month. These revisions preserve the direction of the supporting comparisons; they do not make ASHE, RTI, or A05 populations equivalent. The committed release continues to report its archived June values.
