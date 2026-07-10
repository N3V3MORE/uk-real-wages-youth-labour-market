# Option B Modelling Diagnostics

This report adds a small modelling layer on top of the descriptive ASHE/RTI pipeline. It keeps the same source boundaries and treats the results as diagnostics, not as causal proof.

## Structural-Break Relative-Weight Screen

- 16-17: highest relative-weight break year 2021 with relative weight 50.0%; estimated level shift 6.24 index points.
- 18-21: highest relative-weight break year 2023 with relative weight 29.4%; estimated level shift 3.03 index points.
- 22-29: highest relative-weight break year 2024 with relative weight 59.3%; estimated level shift 3.01 index points.
- 30-39: highest relative-weight break year 2024 with relative weight 89.5%; estimated level shift 3.10 index points.
- 40-49: highest relative-weight break year 2024 with relative weight 91.0%; estimated level shift 3.02 index points.
- 50-59: highest relative-weight break year 2024 with relative weight 98.5%; estimated level shift 5.11 index points.
- 60+: highest relative-weight break year 2024 with relative weight 50.4%; estimated level shift 7.69 index points.
- Boundary: weights are conditional on one two-mean break with at least two years on each side; they are not no-break posterior probabilities.

## Minimum-Wage Event Framing

- 18-21 versus 22-29, 2023-2025: descriptive DID -0.57 index points.
- Wage-floor context: 18 to 20 floor 24.92pp; adult-threshold floor 9.77pp.
- Threshold context: Mixed threshold context: ASHE 18-21 includes 18-20 workers and 21-year-olds; the adult threshold applies to 21-year-olds from 2024 onward.
- Caveat: Descriptive difference-in-differences framing only; not causal because ASHE age bands, policy thresholds, hours, and composition do not cleanly identify treatment.

## Forecast Baseline

- 18-21 2026: forecast index 97.95 (rough residual band 90.14 to 105.76).
- 18-21 2027: forecast index 98.50 (rough residual band 90.69 to 106.31).
- 22-29 2026: forecast index 104.42 (rough residual band 101.90 to 106.94).
- 22-29 2027: forecast index 105.08 (rough residual band 102.56 to 107.60).

## Boundary

These outputs are modelling diagnostics and decision-support framing. They do not convert the descriptive project into a causal estimate, and they do not replace ASHE as the main annual age-specific wage source.
