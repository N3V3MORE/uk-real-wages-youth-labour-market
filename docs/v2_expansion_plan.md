# V2 Expansion Plan

The next version keeps the same question, but gives the fragile 18-21 result better cross-checks.

The rule is simple: no source should answer a question it cannot answer.

## Source Roles

| Source | Allowed role | Not allowed |
| --- | --- | --- |
| ASHE Table 6 | Main annual age-specific earnings source. | It cannot provide 2026 age-specific wages until ASHE 2026 exists in the pipeline. |
| ASHE region by age | Annual regional age-specific earnings source. | It should not be treated as monthly evidence. |
| PAYE RTI | Monthly age-specific PAYE pay and payrolled-employment check. | It does not replace ASHE and does not cover self-employment income. |
| ASHE hourly pay and hours | Descriptive split between hourly pay, paid hours, and residual movement. | It is not a causal explanation. |
| GOV.UK minimum wage rates | Policy wage-floor context for young workers. | It does not prove the minimum wage caused ASHE changes. |
| A05 SA | Youth employment, unemployment, and inactivity context. | It is not an earnings source. |
| EARN01 | Monthly whole-economy or sector wage trend. | It is not age-specific evidence. |

## Build Order

1. Add the source-role guardrails in docs and methodology.
2. Add PAYE RTI age-pay triangulation.
3. Add ASHE hourly pay versus hours decomposition.
4. Add minimum wage policy context.
5. Update claims, evidence files, dashboard, README, and the research note.
6. Add CI after the data work has focused tests.

## Wording Rules

- ASHE remains the main annual age-specific wage source.
- RTI is monthly PAYE evidence, not an ASHE replacement.
- RTI 18-24 does not exactly match ASHE 18-21 or 22-29.
- Weekly, hourly, and monthly pay should not be blurred.
- EARN01 should not be described as age-specific.
- The project should not claim ASHE 2026 age-specific wages unless ASHE 2026 is added.
- Minimum wage analysis is context, not causal proof.
