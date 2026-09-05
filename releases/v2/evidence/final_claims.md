# UK Youth Real-Wage Claims Report

## Executive Summary

- **Bottom line.** The evidence does not support a simple claim that 18-21 workers clearly became better or worse off in real earnings terms after 2019. The baseline ASHE CPIH comparison shows 18-21 real earnings change of -1.81% from 2019 to 2025. The 18-21 real-earnings result is ambiguous and specification-dependent; state the baseline, deflator, worker definition, and earnings measure when discussing it.
- **ASHE 22-29.** Baseline ASHE shows 22-29 real earnings change of 3.57% from 2019 to 2025; its assessment is moderately robust. This remains an annual ASHE age-group finding.
- **Current and contextual sources should stay in their lanes.** EARN01 is a whole-economy wage trend, RTI is monthly PAYE age-pay triangulation, A05 is labour-market stress context, and minimum-wage rates are wage-floor context rather than causal proof.
- **The practical reporting line is qualified.** Use ASHE as the anchor, use RTI and EARN01 as triangulation, keep hours visible, and avoid turning descriptive diagnostics into causal claims.

## What the evidence supports

- **18-21 ASHE real earnings:** Verdict: not robust / ambiguous. Baseline real earnings changed -1.81% from 2019 to 2025; Core specs: 3/6 material disagreements; directional fragility 50.0%.
- **22-29 ASHE real earnings:** Verdict: moderately robust. Baseline real earnings changed 3.57% from 2019 to 2025; Core specs: 1/6 material disagreements; directional fragility 16.7%.
- **Youth labour-market stress:** Verdict: descriptive / corroborating stress signal. Latest A05 16-24 vs 25-34 gap changes since 2019: unemployment 3.70pp; inactivity 2.68pp.
- **Hourly pay versus hours:** Verdict: descriptive decomposition. For 18-21, real weekly earnings changed -1.81% from 2019 to 2025; hourly pay contributed 0.143 log points, hours contributed -0.228, and the residual was 0.067.
- **Minimum wage context:** Verdict: policy context only. The 18 to 20 statutory hourly rate is 10.85 in April 2026; its real statutory wage index is 133.87 with April 2019 = 100.
- **Option B modelling diagnostics:** Verdict: modelling diagnostics / not causal. Option B adds structural break, event framing, and forecast baseline diagnostics.

## Evidence by source

### ASHE 18-21 and robustness

The 18-21 result is the main point that needs careful wording. Claim assessment verdict: not robust. Material 18-21 disagreements are driven by: baseline_year, wage_measure, work_status.
No one-way near-zero sign flips were found for 18-21. ASHE uncertainty and quality evidence: 18-21 median weekly CV is 1.80% (precise), from the ASHE CV workbook. This is a source quality marker, not a constructed confidence interval. 18-21: point estimate -1.81%; approximate two-CV band -6.29% to 2.67% (includes zero).

**Interpretation:** The 18-21 real-earnings result is ambiguous and specification-dependent; state the baseline, deflator, worker definition, and earnings measure when discussing it.

### ASHE 22-29

The 22-29 ASHE assessment is moderately robust: ASHE uncertainty and quality evidence: 22-29 median weekly CV is 0.40% (precise), from the ASHE CV workbook. This is a source quality marker, not a constructed confidence interval. This is still annual ASHE evidence, not a monthly wage signal.

### Current monthly wage trend (EARN01)

Latest whole-economy EARN01 month: 2026-04; real regular pay index 105.05; real total pay index 106.68.
The triangulation report compares ASHE with EARN01 and records that EARN01 is not age-specific.
Directional concordance with EARN01 regular pay for ASHE 18-21: 83% across 6 adjacent year-over-year comparisons; latest cross-source index difference -6.63 index points.
**Interpretation:** EARN01 provides a current whole-economy wage trend and should not be interpreted as age-specific evidence for 18-21 or 22-29 workers.

### RTI monthly age-pay triangulation

RTI 18-24 real median monthly PAYE pay changed 6.22% from January 2019 to 2026-05-01; latest-month flash/provisional flag: True.
The RTI triangulation report compares RTI 18-24 with ASHE 18-21 and 22-29, and records the age-band mismatch.
April-to-April RTI-ASHE concordance for RTI 18-24 versus ASHE 18-21: 100% across 6 adjacent year-over-year comparisons; latest cross-source index difference -7.95 index points.
**Interpretation:** RTI provides monthly PAYE age-pay triangulation, not a replacement for ASHE.

### Wage-floor, hours, and modelling context

Hourly pay versus hours remains a descriptive accounting split, not a causal explanation. The minimum wage context report uses GOV.UK rates from April 2019 onward and flags the statutory age-threshold mismatch. Minimum wage changes provide context, not causal proof of ASHE changes.
- Highest relative break-year weight: 50-59 in 2024 (98.5%); level shift 5.11 index points.
- Minimum-wage event framing: 18-21 versus 22-29 descriptive DID -0.57 index points (-0.48 percentage points on percent-change scale); threshold context is mixed.
- Forecast baseline: 18-21 2026 index 97.95; band type is rough residual band.

## Recommended wording

- **18-21:** The 18-21 real-earnings result is ambiguous and specification-dependent; state the baseline, deflator, worker definition, and earnings measure when discussing it.
- **22-29:** The 22-29 baseline result is assessed as moderately robust; report the signed change with the tested assumptions.
- **EARN01:** EARN01 provides a current whole-economy wage trend, not age-specific evidence for 18-21 or 22-29 workers.
- **RTI:** RTI provides monthly PAYE age-pay triangulation, not a replacement for ASHE.
- **Hours and wage floors:** Weekly earnings changes can be decomposed into hourly pay, hours, and residual movement; use minimum wage rates as wage-floor context for young workers, not as a causal claim.
- **Option B:** Use Option B outputs as relative structural-break weights, mixed-threshold event framing, and rough forecast-baseline diagnostics rather than as official forecasts or causal estimates.

## Further questions

- Would the 18-21 result strengthen if the next ASHE release keeps the negative weekly-earnings signal under the core specifications?
- Does the 18-24 RTI PAYE series keep pointing differently once flash months are revised and more non-flash months are available?
- Are the 18-21 movements mostly a paid-hours story, a worker-composition story, or both?
- Do source quality, work-status splits, or source-triangulation checks move away from the baseline ASHE result for 22-29?

## Caveats and assumptions

ASHE, RTI, A05, EARN01, and minimum-wage data measure different populations, frequencies, and concepts. This is the source limitation that prevents stronger wording.

RTI is PAYE administrative data. It covers payrolled employees, not self-employment or all income. It measures monthly pay, not ASHE weekly or hourly earnings. RTI 18-24 does not exactly match ASHE 18-21 or 22-29.

ASHE age bands do not line up exactly with statutory minimum-wage thresholds. Minimum wage changes provide context, not causal proof of ASHE changes.

The decomposition uses ASHE medians from separate tables. It can separate hourly pay, hours, and residual movements descriptively, but it is not a causal explanation.

These outputs add modelling context, but they do not replace ASHE, do not identify causal effects, and do not provide official forecasts.
