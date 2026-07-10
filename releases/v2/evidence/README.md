# v2 Evidence Package

This folder is packaged evidence for reviewer inspection.
Raw data, processed data, and chart paths referenced by the lineage files are rebuild-only and are not copied into this folder.
sources.lock.yaml fixes source bytes; requirements.lock constrains Python dependencies.
Rebuild the package with:

```powershell
python -m uk_wages.pipeline --all --locked
```

Files:

- `final_claims.md` - Qualified claim wording for public summaries.
- `research_note.md` - Narrative research note generated from current outputs.
- `age_group_real_earnings_change.csv` - Main ASHE real earnings change table by age group.
- `fragility_scores.csv` - Robustness and material-disagreement score table.
- `fragility_diagnostics.md` - Detailed diagnostics for robustness specifications.
- `source_value_checks.csv` - Raw-to-processed source value audit checks.
- `ashe_quality_availability.md` - Availability of ASHE quality and reliability fields.
- `ashe_uncertainty_bands.md` - Approximate ASHE uncertainty bands from published quality measures.
- `ashe_composition_audit.md` - Audit of ASHE composition and coverage changes.
- `triangulation_summary.csv` - ASHE and EARN01 triangulation summary.
- `rti_ashe_annual_summary.csv` - Annual RTI and ASHE triangulation summary.
- `claim_confidence_ladder.csv` - Structured confidence classification for reviewer claims.
- `claim_confidence.md` - Reviewer-facing explanation of claim confidence.
- `headline_number_lineage.csv` - Structured lineage from headline numbers to source evidence.
- `headline_number_lineage.md` - Reviewer-facing headline-number lineage.
- `option_b_ds_report.md` - Option B diagnostic report and modelling caveats.
- `sources.lock.yaml` - Locked source URLs and SHA-256 hashes.
- `requirements.lock` - Python dependency constraints for the release environment.

Use `manifest.json` to verify file sizes and SHA-256 hashes.
