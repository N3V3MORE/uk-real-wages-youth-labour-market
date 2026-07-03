# v1 Evidence Package

This folder is the small, committed evidence snapshot for review. It is rebuilt from ignored raw, processed, and output data with:

```powershell
python -m uk_wages.pipeline --all --locked
```

Files:

- `final_claims.md` - Qualified claim wording for public summaries.
- `age_group_real_earnings_change.csv` - Main ASHE real earnings change table by age group.
- `fragility_scores.csv` - Robustness and material-disagreement score table.
- `source_value_checks.csv` - Raw-to-processed source value audit checks.
- `headline_lineage.csv` - Lineage from public headlines to source evidence artifacts.
- `research_note.md` - Narrative research note generated from current outputs.

Use `manifest.json` to verify file sizes and SHA-256 hashes.
