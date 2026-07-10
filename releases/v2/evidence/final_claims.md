# Final Claims

Use these claim wordings when describing the current outputs.

## Claim 1: 18-21 real earnings

Verdict: fragile / ambiguous

Primary evidence:
The baseline ASHE CPIH comparison shows 18-21 real earnings change of -1.81% from 2019 to 2025.

Robustness evidence:
Claim assessment verdict: not robust.
Core specs: 3/6 material disagreements; directional fragility 50.0%.
Material 18-21 disagreements are driven by: baseline_year, wage_measure, work_status.
No one-way near-zero sign flips were found for 18-21.
ASHE uncertainty and quality evidence: 18-21 median weekly CV is 1.80% (precise), from the ASHE CV workbook. This is a source quality marker, not a constructed confidence interval.
18-21: point estimate -1.81%; approximate two-CV band -6.37% to 2.75% (includes zero).

Caveats:
The evidence does not support a simple claim that 18-21 workers clearly became better or worse off in real earnings terms after 2019. The result moves under reasonable specification choices.

Recommended wording for the policy brief and dashboard:
The 18-21 real-earnings result is ambiguous and specification-dependent; state the baseline, deflator, worker definition, and earnings measure when discussing it.

## Claim 2: 22-29 real earnings

Verdict: moderately robust

Primary evidence:
The baseline ASHE CPIH comparison shows 22-29 real earnings change of 3.57% from 2019 to 2025.

Robustness evidence:
Core specs: 1/6 material disagreements; directional fragility 0.0%.
ASHE uncertainty and quality evidence: 22-29 median weekly CV is 0.40% (precise), from the ASHE CV workbook. This is a source quality marker, not a constructed confidence interval.

Caveats:
This is still an annual ASHE age-group finding, not monthly evidence.

Recommended wording for the policy brief and dashboard:
The 22-29 result is more stable than the 18-21 result, but should still be reported with the tested assumptions.

## Claim 3: Youth labour-market stress

Verdict: descriptive / corroborating stress signal

Primary evidence:
Latest A05 16-24 vs 25-34 gap changes since 2019: unemployment 3.70pp; inactivity 2.68pp.

Robustness evidence:
A05 is a separate labour-market dataset. It can show stress conditions, but it cannot validate age-specific ASHE wage changes.

Caveats:
A05 is rolling three-month labour-market evidence and is not an earnings dataset.

Recommended wording for the policy brief and dashboard:
Use A05 as labour-market stress context, not as proof of age-specific wage movements.

## Claim 4: Current monthly wage trend

Verdict: descriptive only

Primary evidence:
Latest whole-economy EARN01 month: 2026-04; real regular pay index 105.05; real total pay index 106.68.

Supporting evidence:
The triangulation report compares ASHE with EARN01 and records that EARN01 is not age-specific.
Directional concordance with EARN01 regular pay for ASHE 18-21: 83% across 6 adjacent year-over-year comparisons; latest regular-pay gap -6.96pp.

Caveats:
EARN01 is not age-specific; it provides a current whole-economy wage trend and should not be interpreted as age-specific evidence.

Recommended wording for the policy brief and dashboard:
EARN01 provides a current whole-economy wage trend, not age-specific evidence for 18-21 or 22-29 workers.

## Claim 5: RTI monthly age-pay triangulation

Verdict: descriptive / source-bounded

Primary evidence:
RTI 18-24 real median monthly PAYE pay changed 6.22% from January 2019 to 2026-05-01; latest-month flash/provisional flag: True.

Supporting evidence:
The RTI triangulation report compares RTI 18-24 with ASHE 18-21 and 22-29, and records the age-band mismatch.
April-to-April RTI-ASHE concordance for RTI 18-24 versus ASHE 18-21: 100% across 6 adjacent year-over-year comparisons; latest level gap -7.95pp.

Caveats:
RTI is PAYE administrative data. It covers payrolled employees, not self-employment or all income. It measures monthly pay, not ASHE weekly or hourly earnings. RTI 18-24 does not exactly match ASHE 18-21 or 22-29.

Recommended wording for the policy brief and dashboard:
RTI provides monthly PAYE age-pay triangulation, not a replacement for ASHE.

## Claim 6: Hourly pay versus hours

Verdict: descriptive decomposition

Primary evidence:
For 18-21, real weekly earnings changed -1.81% from 2019 to 2025; hourly pay contributed 0.143 log points, hours contributed -0.228, and the residual was 0.067.

Supporting evidence:
The ASHE decomposition report confirms the weekly, hourly, and paid-hours workbooks were available and keeps a residual term.

Caveats:
The decomposition uses ASHE medians from separate tables. It can separate hourly pay, hours, and residual movements descriptively, but it is not a causal explanation.

Recommended wording for the policy brief and dashboard:
Weekly earnings changes can be decomposed into hourly pay, hours, and residual movement; do not describe the decomposition as proof of cause.

## Claim 7: Minimum wage context

Verdict: policy context only

Primary evidence:
The 18 to 20 statutory hourly rate is 10.85 in April 2026; its real statutory wage index is 133.87 with April 2019 = 100.

Supporting evidence:
The minimum wage context report uses GOV.UK rates from April 2019 onward and flags the statutory age-threshold mismatch.

Caveats:
ASHE age bands do not line up exactly with statutory minimum-wage thresholds. Minimum wage changes provide context, not causal proof of ASHE changes.

Recommended wording for the policy brief and dashboard:
Use minimum wage rates as wage-floor context for young workers, not as a causal claim.

## Claim 8: Option B modelling diagnostics

Verdict: modelling diagnostics / not causal

Primary evidence:
Option B adds structural break, event framing, and forecast baseline diagnostics.
Highest relative break-year weight: 50-59 in 2024 (98.5%); level shift 5.11 index points.
Minimum-wage event framing: 18-21 versus 22-29 descriptive DID -0.57 index points; threshold context is mixed.
Forecast baseline: 18-21 2026 index 97.95; band type is rough residual band.

Caveats:
These outputs add modelling context, but they do not replace ASHE, do not identify causal effects, and do not provide official forecasts.

Recommended wording for the policy brief and dashboard:
Use Option B outputs as relative structural-break weights, mixed-threshold event framing, and rough forecast-baseline diagnostics rather than as official forecasts or causal estimates.

## What Would Change This Conclusion?

For the 18-21 claim, the evidence would strengthen if ASHE quality evidence stays reliable, the negative weekly-earnings result survives core specifications, hourly pay, weekly pay, full-time rows, and RTI all point in the same direction.

The 18-21 claim would weaken if ASHE quality flags are poor, the negative result disappears under full-time-only or mean earnings, the result is mostly a paid-hours story, or RTI continues to point differently for the wider 18-24 PAYE group.

The 22-29 claim would strengthen if quality flags remain reliable and robustness checks keep agreeing. It would weaken if work-status, composition, or source-triangulation checks move away from the baseline ASHE result.

The source limitation that prevents stronger wording is unchanged: ASHE, RTI, A05, EARN01, and minimum-wage data measure different populations, frequencies, and concepts.
