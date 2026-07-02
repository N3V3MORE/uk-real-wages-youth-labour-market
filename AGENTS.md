# Project Instructions

This project analyses whether UK workers, especially younger workers, became better or worse off after inflation since 2019.

Build a reproducible Python research project. Prefer modular scripts over one-off notebook code.

Use official ONS data sources only unless explicitly instructed otherwise.

Core datasets:
- ONS MM23 Consumer Price Inflation Time Series
- ONS ASHE Table 6: Earnings and hours worked, age group
- ONS Earnings and hours worked, UK region by age group
- ONS A05 SA: Employment, unemployment and economic inactivity by age group
- ONS EARN01: Average weekly earnings

Use CPIH all-items index as the default deflator. Use CPI as a sensitivity check.

Key formula:

```text
real_wage_index = nominal_earnings_index / price_index * 100
```

Set 2019 = 100 for the main annual ASHE analysis. Set January 2019 = 100 for the monthly EARN01 analysis.

Be explicit that:
- ASHE is annual and age-specific.
- EARN01 is monthly but not age-specific.
- A05 SA is rolling three-monthly and seasonally adjusted.
- 2026 age-specific wage analysis is limited unless ASHE 2026 is available.
- ONS labels A05 SA as official statistics in development.

Every chart must have:
- Clear title
- Source note
- Deflator note
- Date range
- Units

Do not hardcode local file paths. Cache downloaded raw data. Save cleaned data to `data/processed`. Save final charts to `outputs/charts`. Save final tables to `outputs/tables`. Write a methodology note explaining all transformations.

