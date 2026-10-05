# UK Youth Real-Wage Report

## Executive Summary

- The baseline 18-21 result is assessed as not robust. Baseline ASHE shows 18-21 real median weekly earnings at -1.81% from 2019 to 2025, but 3 of 6 core robustness checks materially change the result.
- **The wider 18-24 monthly PAYE signal.** RTI real median monthly pay rose by 6.22% from January 2019 to 2026-05-01. The latest month is flagged as an early estimate. 2026-04-01 is the latest non-flash month.
- **Hourly pay and hours inside ASHE.** For 18-21, real hourly pay changed by 15.33%, while total paid hours are -20.40%; Separate medians leave an arithmetic residual, so the split remains descriptive.
- **ASHE publishes a 22-29 comparator.** Baseline ASHE 22-29 real weekly earnings changed by 3.57%, while A05 shows the 16-24 Feb-Apr 2026 unemployment gap versus 25-34 changed by 3.70 percentage points and the inactivity gap by 2.68 points.

This note describes saved source editions. 'Latest' refers to the inputs used for this build; source releases and hashes are recorded in `config/sources.lock.yaml`. The headline compares gross earnings for employee jobs, rather than disposable household income or pay histories for the same people.

## The youngest-adult wage signal is not robust

ASHE is the main annual age-specific earnings source, and the baseline result uses median weekly gross earnings from the published all-sex, all-work-status employee-job rows, deflated with April CPIH. The baseline age-group changes are: 18-21 is -1.81% from 2019 to 2025, compared with 3.57% for 22-29, 4.05% for 30-39, and 0.50% for 16-17. The strongest age group in the table is 60+, at 10.26%.

The sensitivity count describes configured comparisons, not independent statistical trials or the probability that a claim is true. Changing the start year measures a different interval; mean earnings describe a different statistic; full-time-only rows cover a different population. The stress tests excluding 2020 from the intervening path or restricting displayed age groups preserve endpoint estimates for retained groups.

The headline should still be qualified. The robustness harness changes defensible assumptions around baseline year, wage measure, deflator, worker definition, and the treatment of 2020. For 18-21, 3 of 6 core checks create material disagreements. The baseline ASHE weekly-earnings change is -1.81%, and the assessed robustness is not robust.

The practical implication is that the top-line number should not travel alone. A reader needs to see the ASHE age group, weekly-earnings measure, CPIH deflator, latest ASHE year, and robustness result next to the headline. Without that context, the baseline estimate can sound more decisive than the evidence warrants.

There is no current ASHE 25-34 wage row in the processed age-specific ASHE outputs. That matters because 25-34 appears in RTI and A05, but it should not be treated as if the ASHE wage pipeline has the same age band. Where the project uses 25-34, it is using a source that actually publishes 25-34, not filling an ASHE gap.

For 18-21, the latest ASHE median weekly CV is 1.80% (precise).
For 22-29, the latest ASHE median weekly CV is 0.40% (precise).

Report the 18-21 baseline change with its not robust assessment. Keep the source, wage measure, deflator, and worker definition attached whenever it is quoted.

## RTI extends the clock but changes the population

RTI adds a monthly PAYE check through 2026-05-01. For 18-24, real median monthly PAYE pay is 6.22% from January 2019 to 2026-05-01; payrolled employees are -2.86% over the same baseline. The latest month is flagged as an early estimate. 2026-04-01 is the latest non-flash month.

RTI adds context to the ASHE picture. RTI 18-24 overlaps ASHE 18-21 and part of ASHE 22-29; it also measures monthly PAYE pay rather than ASHE weekly earnings or hourly rates. RTI adds a separate monthly PAYE check for the wider 18-24 group; any disagreement needs to be interpreted within those source boundaries.

The timing is different too. ASHE is an annual April snapshot of employee jobs, while RTI is monthly PAYE administrative data. RTI can therefore move with changes in monthly hours, job mix, bonuses, and payrolled employment during the year. That makes it valuable for recency, but it also means a monthly RTI improvement is not automatically a like-for-like correction to an annual ASHE weekly-earnings result.

Use RTI for PAYE triangulation within the saved release's coverage, especially beyond the latest ASHE year, with its age band and monthly earnings concept attached.

## Hourly pay, paid hours, and weekly earnings

The ASHE decomposition compares changes in median weekly gross pay, median hourly gross pay, and median total paid hours, retaining an arithmetic residual. These separate medians do not identify a causal mechanism.

For 18-21, real weekly earnings are -1.81% from 2019 to 2025. Real hourly pay changed by 15.33%, while total paid hours are -20.40%. In log terms, hourly pay contributes 0.143, hours contribute -0.228, and the residual is 0.067. For 22-29, real weekly earnings changed by 3.57%, real hourly pay changed by 4.45%, and hours are -0.53%.

The computed decomposition groups in the current output are 18-21, 22-29, 30-39. The requested groups without a computed row are 25-34. Those missing rows are not filled in; if ASHE Table 6 does not publish the required weekly, hourly, and hours rows for an age group, the honest output is an explicit absence.

The residual is important. The decomposition combines medians from separate ASHE tables, so hourly pay, paid hours, and weekly pay do not have to multiply back together exactly. The residual is the arithmetic gap left after the hourly-pay and hours movements are combined. It can reflect distributional differences across tables, changes in worker mix, or other measurement boundaries; it should not be labelled as an unexplained behavioural channel.

For 18-21, weekly earnings and hourly pay move differently. Paid hours matter to interpretation, and the separate medians and residual limit this to a descriptive comparison.

## Wage floors and labour-market stress add context, not causality

The 18-20 statutory hourly rate moves from GBP 6.15 in April 2019 to GBP 10.85 in April 2026. After April CPIH deflation, the real statutory wage index for 18-20 is 133.87 with April 2019 set to 100. For ASHE 18-21, the 18-20 statutory rate is 0.721 of median hourly pay in 2019 and 0.794 in 2025. For ASHE 22-29, the adult threshold is 0.691 of median hourly pay in 2019 and 0.769 in 2025.

The minimum-wage thresholds also move over the period. ASHE 18-21 includes 21-year-olds, while the 18-20 statutory band does not. The adult threshold was 25+ before April 2021, 23+ from April 2021, and 21+ from April 2024. That shifting boundary is why the report treats minimum wage as wage-floor pressure rather than a clean treatment assignment.

For 18-21, all-employee nominal weekly pay changed by 25.66%, full-time by 42.43%, part-time by 48.20%, and paid hours by -20.40%.
For 22-29, all-employee nominal weekly pay changed by 32.54%, full-time by 31.06%, part-time by 42.28%, and paid hours by -0.53%.

These composition pay changes are nominal. Published job-count ratios provide descriptive proxies for the mix of jobs; they are not weights that reconstruct an all-employee median. No composition-adjusted wage change is estimated.

A05 is not an earnings source, but it shows the labour-market backdrop around young people. In Feb-Apr 2026, the 16-24 unemployment gap versus 25-34 changed by 3.70 percentage points since 2019, and the inactivity gap changed by 2.68 points. The baseline is the mean of rolling periods ending in 2019. Here, 25-34 is a labour-market comparator, not an ASHE wage comparator.

The saved wage-floor, composition, and labour-market figures provide context. They do not identify why ASHE medians moved.

## Recommended next steps

- **Use qualified headline wording.** Report the baseline ASHE 18-21 weekly-earnings change of -1.81% with its not robust assessment, and keep the measure, deflator, worker definition, and baseline year visible.
- **Monitor the next ASHE release first.** A clearer conclusion needs the next annual age-specific ASHE update and the same robustness harness rerun against it.
- **Track RTI non-flash months separately.** RTI is useful for timeliness, but the latest flash month should not override the cleaner non-flash signal.
- **Keep hours visible.** Any dashboard or brief should pair weekly earnings with hourly pay and paid-hours movement for 18-21.

## Further questions

- Do full-time, part-time, and sex-specific ASHE rows continue to move differently for 18-21 when the next release lands?
- Does RTI 18-24 keep diverging from ASHE 18-21 once flash months are revised?
- Can additional cuts such as student status, region, or occupation explain the paid-hours movement without overclaiming beyond published data?

## Caveats and assumptions

ASHE remains the main annual age-specific wage source. The latest ASHE age-specific data in this output stop at 2025. Monthly and contextual sources may extend further, but they do not supply later ASHE age-specific wages.

The sources measure different populations, frequencies, and concepts. ASHE is an annual April snapshot of employee jobs; RTI is monthly PAYE administrative data; A05 is a rolling labour-market status table; EARN01 is whole-economy pay; and the minimum-wage series is a statutory hourly floor. The report compares them only when their boundaries remain explicit.

ASHE-EARN01 comparisons use April observations for both sources and set April 2019 to 100. This avoids comparing an April snapshot with a calendar-year average or a January baseline. Differences are reported in index points; they are not differences in pay levels. Directional agreement describes overlapping adjacent years and cannot establish that the sources cover the same workers.

The robustness harness tests specification sensitivity, not sampling uncertainty. It asks whether the result survives reasonable choices about baseline year, deflator, earnings measure, worker definition, and the treatment of 2020. The quality audit separately checks published ASHE CV workbooks where they exist, but it does not invent confidence intervals when the source does not provide enough evidence.

ASHE is an April reference-period survey of employee jobs. Gross weekly earnings are before deductions and are not annual or household income. Successive age bands contain different jobs and people. Aggregate CPIH does not measure inflation specific to young people or individual households. A05 covers rolling three-month periods and is official statistics in development.

Published CVs describe sampling precision. They do not rule out coverage or non-response bias; source-value checks verify selected transformations rather than survey representativeness. This project does not estimate causal effects, model student status, or quantify household living standards.

## Earlier research and contribution

The broad question is established. [Resolution Foundation (November 2023)](https://www.resolutionfoundation.org/comment/falling-pay-divergent-data-and-a-bulging-middle/) examines age-specific real weekly pay since 2019; its [December 2023 youth report](https://www.resolutionfoundation.org/publications/narrowing-the-youth-gap/) discusses hourly pay and hours. [Henry and Joyce (IFS, May 2024)](https://ifs.org.uk/sites/default/files/2024-05/What-has-happened-to-earnings-IFS-Report_0.pdf) compare earnings sources. [Forth and colleagues (online 2025; 2026 issue)](https://openaccess.city.ac.uk/id/eprint/35689/) examine ASHE representativeness.

This is a replication and update exercise with reproducible inputs and explicit sensitivity comparisons. Earlier figures can be checked numerically only after aligning their periods, editions, populations, earnings statistics, and deflators. The project makes no claim that its broad question or descriptive hours comparison is new.
