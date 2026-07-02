# Project Instructions

This project studies whether UK workers, especially younger workers, became better or worse off after inflation since 2019.

Use official ONS data unless the user explicitly changes scope. Keep the command-line pipeline as the source of truth; notebooks are not part of the reproducible path.

Core sources:

- ONS MM23 Consumer Price Inflation Time Series.
- ONS ASHE Table 6: earnings and hours worked by age group.
- ONS ASHE UK region by age group.
- ONS A05 SA: employment, unemployment, and economic inactivity by age group.
- ONS EARN01: average weekly earnings.

Use CPIH all-items as the default deflator and CPI as a sensitivity check.

```text
real_wage_index = nominal_earnings_index / price_index * 100
```

Set 2019 = 100 for annual ASHE analysis. Set January 2019 = 100 for monthly EARN01 analysis.

Be explicit about the limits:

- ASHE is annual and age-specific.
- EARN01 is monthly but not age-specific.
- A05 SA is rolling three-month labour-market data.
- A05 SA is labelled by ONS as official statistics in development.
- Do not describe the project as having a 2026 age-specific wage result unless ASHE 2026 is available.

Charts need a title, source note, deflator note, date range, and units.

Do not hardcode local paths. Cache raw downloads under `data/raw`, write cleaned files to `data/processed`, charts to `outputs/charts`, tables to `outputs/tables`, and evidence files to `outputs/evidence`.
