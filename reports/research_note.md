# Real Wages and Youth Labour Market Stress in the UK, 2019-2026

## 1. Short Answer

The 18-21 real-wage result is still not a clean win or loss. In the baseline ASHE run, median weekly earnings for 18-21 year-olds are -1.81% in real CPIH terms from 2019 to 2025. That finding is fragile: 3 of 7 core robustness checks create a material disagreement.

RTI monthly PAYE data shows 18-24 median monthly pay 6.22% from January 2019 to 2026-05-01, although that latest month is flagged as an early estimate. The ASHE decomposition helps account for the tension: for 18-21 year-olds, real hourly pay rose, but total paid hours fell sharply.

The 22-29 ASHE result is steadier. Baseline real weekly earnings are up 3.57% from 2019 to 2025, and the decomposition shows hourly pay doing most of the work. A05 shows the 16-24 unemployment gap has widened by 3.70 percentage points versus 25-34 since 2019; the inactivity gap has widened by 2.68 points.

## 2. Why This Is Hard To Answer

ASHE is the strongest source for annual age-specific earnings, but the current ASHE age-specific data stop at 2025 provisional. The project title includes 2026 because other sources extend into 2026, not because ASHE provides 2026 age-specific wages.

RTI gives a more current monthly view and includes age bands, but it is PAYE administrative data. It covers payrolled employees, excludes self-employment income, and measures monthly pay. That is useful triangulation, but it is not the same thing as ASHE weekly earnings.

Age bands also do not line up neatly. RTI has 18-24. ASHE has 18-21 and 22-29. Minimum wage policy uses thresholds such as 18-20, 21+, 23+, and 25+. A single age label can therefore mix workers facing different policy rules, different hours, and different work patterns.

Weekly earnings combine hourly pay and hours worked. If hourly pay rises while paid hours fall, weekly earnings can look flat or negative. That is why the v2 pipeline adds the ASHE hourly-pay and hours decomposition.

The measures also use different clocks. ASHE is an annual April snapshot of employee jobs. RTI is monthly PAYE administrative data, so it can move with changes in hours, job mix, bonuses, and payrolled employment during the year. A05 is a rolling labour-market status table, not a pay table. The minimum-wage series is a statutory hourly floor. Putting those sources side by side is useful only if each one keeps its own job.

## 3. ASHE Baseline Result

The baseline ASHE result uses median weekly gross earnings for all employee jobs and deflates them with April CPIH.

- 18-21 real median weekly earnings are -1.81%.
- 22-29 real median weekly earnings are up 3.57%.
- 30-39 real median weekly earnings are up 4.05%.
- 16-17 real median weekly earnings are up 0.50%.
- 60+ is the strongest age group in the baseline table, up 10.26%.

So the narrow ASHE baseline says the youngest adult group is the weak spot. It does not say that all younger workers lost ground. It also does not say anything about 2026 age-specific ASHE wages.

There is also no current ASHE 25-34 wage row in the processed age-specific ASHE outputs. That matters because 25-34 appears in RTI and A05, but it should not be treated as if the ASHE wage pipeline has the same age band. Where the project uses 25-34, it is using a source that actually publishes 25-34, not filling an ASHE gap.

## 4. Why The 18-21 Result Is Fragile

The robustness harness changes defensible assumptions: baseline year, wage measure, deflator, worker definition, and the treatment of 2020. For 18-21, 3 of 7 core checks create material disagreements.

That matters because the baseline result is small enough to move. The right wording is not that 18-21 workers clearly became worse off. The right wording is: on the baseline ASHE weekly-earnings measure, 18-21 is down, but the direction and size are specification-dependent.

This is specification sensitivity, not sampling uncertainty. The harness asks whether the conclusion survives reasonable choices about baseline year, deflator, earnings measure, worker definition, and the treatment of 2020. It does not estimate confidence intervals for ASHE medians, and it does not use ASHE quality flags to draw uncertainty bands. The output should therefore be read as a robustness audit of the modelling choices made here.

## 5. What RTI Adds

RTI adds a monthly PAYE check that reaches into 2026. For 18-24, real median monthly PAYE pay is 6.22% from January 2019 to 2026-05-01. The same RTI row shows payrolled employees -2.86% from January 2019. The latest available month is flagged as an early estimate; 2026-04-01 is the latest non-flash month in the current output.

This complicates the ASHE picture rather than replacing it. RTI 18-24 overlaps ASHE 18-21 and part of ASHE 22-29. It also captures monthly PAYE pay, not weekly earnings or hourly rates.

The latest RTI month is useful because it reaches beyond ASHE, but it should carry less weight than the non-flash months. The current report keeps both dates visible for that reason: the latest available month shows the most current PAYE signal, while the latest non-flash month is the cleaner check against revision-prone data. Neither date turns RTI into an ASHE substitute.

## 6. Hourly Pay Versus Hours

The decomposition reads ASHE weekly gross pay, hourly gross pay, hourly pay excluding overtime, total paid hours, and basic paid hours. The headline split uses gross hourly pay and total paid hours.

For 18-21, real weekly earnings are -1.81% from 2019 to 2025. Real hourly pay is up 15.33%, while total paid hours are -20.40%. In log terms, hourly pay contributes 0.143, hours contribute -0.228, and the residual is 0.067.

For 22-29, real weekly earnings are up 3.57%, real hourly pay is up 4.45%, and hours are -0.53%.

The computed decomposition groups in the current output are 18-21, 22-29, 30-39. The requested groups without a computed decomposition row are 25-34. Those missing rows are not filled in. If ASHE Table 6 does not publish the required weekly, hourly, and hours rows for an age group in this pipeline, the honest output is an explicit absence, not an invented estimate.

This is still not causal. The decomposition uses medians from separate ASHE tables, so the residual matters. The residual is the arithmetic gap left after combining the median hourly-pay movement and median-hours movement. It can reflect the fact that the medians come from different distributions and tables; it should not be read as an unexplained behavioural channel.

## 7. Minimum Wage Context

The 18-20 statutory hourly rate rises from GBP 6.15 in April 2019 to GBP 10.85 in April 2026. After April CPIH deflation, the real statutory wage index for 18-20 is 133.87 with April 2019 set to 100.

For ASHE 18-21, the 18-20 statutory rate is 0.721 of median hourly pay in 2019 and 0.794 in 2025. For ASHE 22-29, the adult statutory threshold is 0.691 of median hourly pay in 2019 and 0.769 in 2025.

Those numbers are context, not causality. ASHE 18-21 includes 21-year-olds, while the 18-20 statutory band does not. The adult threshold also changes over time: 25+ before April 2021, 23+ from April 2021, and 21+ from April 2024.

That shifting threshold is why the minimum-wage section is deliberately framed as wage-floor pressure rather than a causal estimate. A rising statutory floor can make the youth-wage story more plausible, but the tables here do not identify who was paid the floor, how many hours they worked, or whether an observed ASHE median changed because of policy, composition, or hours.

## 8. Youth Labour-Market Stress

A05 is not an earnings source, but it helps describe labour-market pressure around young people. The latest A05 output shows the 16-24 unemployment gap versus 25-34 has widened by 3.70 percentage points since 2019. The inactivity gap has widened by 2.68 percentage points.

Here, 25-34 is a labour-market comparator, not an ASHE wage comparator. A05 publishes the 25-34 status group, so it is a reasonable benchmark for youth unemployment and inactivity gaps. That does not create a matching ASHE 25-34 wage estimate, and it does not mean the A05 gap explains the wage result. It simply says the broader youth labour-market backdrop has become more strained relative to the next older group.

## 9. What We Can And Cannot Conclude

Strongest findings:

- ASHE remains the main annual age-specific wage source.
- Baseline ASHE 18-21 real weekly earnings are -1.81% from 2019 to 2025.
- The 18-21 result is fragile under reasonable specification changes.
- The ASHE decomposition shows 18-21 hourly pay rising while paid hours fall.
- RTI provides monthly PAYE age-pay triangulation into 2026.
- Minimum wage rates rose materially in real terms for young age thresholds.

Things this project does not prove:

- It does not estimate causal effects.
- It does not estimate ASHE sampling uncertainty or publish uncertainty intervals.
- It does not claim ASHE 2026 age-specific wages.
- It does not model student status, local authority differences, or household-specific inflation.
- It does not use EARN01 as age-specific evidence.

## 10. Final Answer

The best answer is cautious. Baseline ASHE says 18-21 real weekly earnings fell slightly from 2019 to 2025, but that result is fragile. RTI says broader 18-24 monthly PAYE pay rose in real terms into 2026. The ASHE decomposition accounts for why both can be true: for 18-21, hourly pay rose, but hours fell enough to pull weekly earnings down. Minimum wage policy gives important wage-floor context, and A05 shows youth labour-market stress has worsened.

So the v2 conclusion is not that young workers simply got better off or worse off. It is that the youth real-wage story is mixed, source-dependent, and strongly affected by hours.
