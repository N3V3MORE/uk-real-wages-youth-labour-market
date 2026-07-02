# Methodology

## Sources

The pipeline uses ONS sources only:

- MM23 Consumer Price Inflation Time Series for CPIH and CPI.
- ASHE Table 6 for annual age-specific earnings.
- ASHE UK region by age group for annual regional age comparisons.
- A05 SA for employment, unemployment, and inactivity by age.
- EARN01 for monthly average weekly earnings.

## Deflating Pay

CPIH all-items is the default deflator. CPI all-items is kept as a sensitivity check.

ASHE is an annual earnings snapshot around April, so the main ASHE calculation uses April CPIH. The processed inflation table also keeps calendar-year average CPIH for sensitivity runs.

```text
real_wage_index = nominal_earnings_index / price_index * 100
```

The annual ASHE index uses 2019 = 100. The monthly EARN01 index uses January 2019 = 100.

## Earnings Measures

The main age comparison uses median weekly gross earnings for all employee jobs. Medians are less exposed to high-earner outliers than means. Mean weekly gross earnings are still cleaned and tested as a sensitivity measure.

## Frequency Limits

ASHE is annual and age-specific. EARN01 is monthly but not age-specific. A05 SA is rolling three-month labour-market data, not earnings data.

The 2026 part of the project title comes from current EARN01, inflation, and A05 SA releases. Age-specific wage statements should stop at the latest ASHE edition unless ASHE 2026 is added.

## A05 16-24 Derivation

The current A05 SA workbook publishes 16-17 and 18-24 separately. The pipeline derives 16-24 by summing employment, unemployment, activity, and inactivity levels for those two age bands, then recomputing rates from the combined levels.

The youth unemployment gap is derived 16-24 unemployment minus 25-34 unemployment. The youth inactivity gap is calculated the same way.
