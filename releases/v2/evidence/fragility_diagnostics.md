# Fragility Diagnostics

## Materiality

Results are treated as materially positive or negative only when the real earnings change is at least 1.0 percentage point away from zero. Smaller sign changes are labelled near-zero or inconclusive.

## Fragility diagnostics for 18-21

Material 18-21 disagreements are driven by: baseline_year, wage_measure, work_status.
No one-way near-zero sign flips were found for 18-21.

## Minimal material-change diagnostics

A material disagreement can change magnitude without reversing sign. The legacy CSV field `material_flip` records material disagreement, not necessarily a sign flip.

Baseline-year alternatives cover different intervals; mean and full-time alternatives change the statistic or population. These are sensitivity checks, not repeated estimates of exactly the same quantity. Counts and verdict labels are not statistical probabilities.

- 16-17: 1 changed assumption(s) (work_status); material disagreement: True; classification near_zero_or_inconclusive to positive_material.
- 18-21: 1 changed assumption(s) (baseline_year); material disagreement: True; classification negative_material to positive_material.
- 22-29: 1 changed assumption(s) (baseline_year); material disagreement: True; classification positive_material to near_zero_or_inconclusive.
- 30-39: 1 changed assumption(s) (work_status); material disagreement: True; classification positive_material to near_zero_or_inconclusive.
- 40-49: 1 changed assumption(s) (work_status); material disagreement: True; classification positive_material to near_zero_or_inconclusive.
- 50-59: 1 changed assumption(s) (work_status); material disagreement: True; classification positive_material to positive_material.
- 60+: 1 changed assumption(s) (work_status); material disagreement: True; classification positive_material to positive_material.

## Recommended policy wording

Use cautious wording for the youngest workers: say the 18-21 real earnings finding is sensitive to baseline and sample choices when material disagreements appear, and do not describe near-zero sign flips as decisive reversals.
