# Claim Confidence Ladder

This reader-facing layer combines baseline results, robustness, source validation, RTI triangulation, ASHE quality evidence, composition checks, decomposition, and source boundaries. It does not replace `claim_assessment.csv`.

## c1_youngest_real_wages

- Confidence: not supported
- Baseline: ASHE 18-21 real weekly earnings changed by -1.81% to 2025.
- Robustness: not robust; 3 of 6 tested specifications materially disagree.
- Quality: ASHE 18-21 median weekly CV is 1.80% (precise).
- Triangulation: RTI 18-24 is a separate PAYE check that complicates direct ASHE wording. Composition audit is available for ASHE work-status and sex rows.
- Public wording: Treat this claim as sensitive to defensible choices. Do not state it as a simple gain or loss; name the baseline, deflator, worker definition, and sample caveats.
- What would change this assessment: The assessment would strengthen if ASHE quality remains reliable, core specifications stay negative, hourly pay, weekly pay, full-time rows, and RTI align; it would weaken if quality flags are poor, full-time-only or mean measures remove the loss, or the result is mostly hours.

## c2_young_workers_vs_prime_age

- Confidence: low confidence
- Baseline: ASHE 18-21 real weekly earnings changed by -1.81% to 2025.
- Robustness: not robust; 3 of 6 tested specifications materially disagree.
- Quality: ASHE 18-21 median weekly CV is 1.80% (precise).
- Triangulation: RTI 18-24 is a separate PAYE check that complicates direct ASHE wording. Composition audit is available for ASHE work-status and sex rows.
- Public wording: Treat this comparison as sensitive to specification choices. Use the young_worker_gap_vs_30_39 metric and state the baseline rather than making a broad youth-worker claim.
- What would change this assessment: The assessment would strengthen if ASHE quality remains reliable and robustness checks agree; it would weaken if source quality, work-status splits, or RTI comparisons point away from the ASHE result.

## c2_22_29_real_wages

- Confidence: medium confidence
- Baseline: ASHE 22-29 real weekly earnings changed by 3.57% to 2025.
- Robustness: moderately robust; 1 of 6 tested specifications materially disagree.
- Quality: ASHE 22-29 median weekly CV is 0.40% (precise).
- Triangulation: RTI 18-24 is a separate PAYE check that complicates direct ASHE wording. Composition audit is available for ASHE work-status and sex rows.
- Public wording: This claim mostly holds across the tested specifications, but it still needs the assumptions attached: Workers aged 22-29 saw real earnings gains since 2019.
- What would change this assessment: The assessment would strengthen if ASHE quality remains reliable and robustness checks agree; it would weaken if source quality, work-status splits, or RTI comparisons point away from the ASHE result.

## c3_inflation_deflator_sensitivity

- Confidence: medium confidence
- Baseline: Baseline result not age-specific in this claim.
- Robustness: robust
- Quality: ASHE quality evidence is not directly relevant to this non-ASHE claim.
- Triangulation: No separate triangulation layer required.
- Public wording: This claim holds across the configured robustness experiments: The headline conclusion is not driven only by choosing CPIH instead of CPI.
- What would change this assessment: The assessment would strengthen if source validation, robustness, and triangulation agree; it would weaken if any source boundary is violated.

## c4_rti_age_pay_triangulation

- Confidence: descriptive only
- Baseline: Baseline result not age-specific in this claim.
- Robustness: descriptive / source-bounded
- Quality: ASHE quality evidence is not directly relevant to this non-ASHE claim.
- Triangulation: RTI is descriptive monthly PAYE triangulation, not an ASHE replacement.
- Public wording: Treat this as descriptive evidence, not an ASHE robustness claim. Use it only within its source boundary: PAYE RTI age-specific monthly pay supports or complicates the ASHE young-worker conclusion.
- What would change this assessment: The assessment would strengthen as a triangulation signal if non-flash RTI months keep the same direction; it would weaken if revisions reverse the monthly PAYE pattern.

## c5_hourly_vs_hours

- Confidence: descriptive only
- Baseline: Baseline result not age-specific in this claim.
- Robustness: descriptive / source-bounded
- Quality: ASHE quality evidence is not directly relevant to this non-ASHE claim.
- Triangulation: ASHE decomposition is descriptive and not causal.
- Public wording: Treat this as descriptive evidence, not an ASHE robustness claim. Use it only within its source boundary: Weak weekly earnings for young workers can be decomposed into hourly pay, hours, and residual movement.
- What would change this assessment: The assessment would strengthen if work-status and quality audits show the same hours story; it would weaken if separate median tables or composition shifts explain most of the split.

## c6_minimum_wage_context

- Confidence: descriptive only
- Baseline: Baseline result not age-specific in this claim.
- Robustness: descriptive / source-bounded
- Quality: ASHE quality evidence is not directly relevant to this non-ASHE claim.
- Triangulation: Minimum wage evidence is wage-floor context only.
- Public wording: Treat this as descriptive evidence, not an ASHE robustness claim. Use it only within its source boundary: Minimum wage changes provide policy context for young-worker pay changes.
- What would change this assessment: The assessment would strengthen as context if ASHE hourly rows near the statutory floor move consistently; it would weaken if age-threshold mismatch or composition dominates.
