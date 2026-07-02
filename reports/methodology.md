# Methodology

## Sources

The pipeline uses official ONS sources only:

- MM23 Consumer Price Inflation Time Series for CPIH and CPI all-items indices.
- ASHE Table 6 for annual age-specific earnings.
- ASHE UK region by age group for annual regional age comparisons.
- A05 SA for employment, unemployment, and inactivity by age.
- EARN01 for monthly average weekly earnings.

## Deflation

CPIH all-items is the default deflator. CPI all-items is retained as a sensitivity series. Annual ASHE earnings are deflated with April CPIH because ASHE is an annual earnings snapshot around April. The processed inflation file also includes calendar-year average CPIH for sensitivity checks.

The core formula is:

```text
real_wage_index = nominal_earnings_index / price_index * 100
```

Annual ASHE indices use 2019 = 100. Monthly EARN01 indices use January 2019 = 100.

The final age-group summary reports the main CPIH-deflated real change and a CPI-deflated sensitivity column.

## Earnings Measures

The main age comparison uses median weekly gross earnings for all employee jobs where available. Medians are preferred because they are less distorted by high earners than means. Mean weekly gross earnings are cleaned as a sensitivity measure.

## Frequency Limits

ASHE is annual and age-specific. EARN01 is monthly but not age-specific. A05 SA is rolling three-monthly and seasonally adjusted. ONS describes A05 SA Labour Force Survey estimates as official statistics in development.

The 2026 part of the project title is supported by current monthly EARN01, inflation, and A05 SA data. Age-specific earnings should only be described through the latest available ASHE edition unless ASHE 2026 becomes available.

## A05 16-24 Derivation

A05 SA publishes separate 16-17 and 18-24 age bands in the current workbook. For the youth comparison, the pipeline derives 16-24 by summing 16-17 and 18-24 employment, unemployment, activity, and inactivity levels, then recomputing rates from those combined levels. The youth unemployment gap is the derived 16-24 unemployment rate minus the 25-34 unemployment rate; the youth inactivity gap is calculated the same way.
