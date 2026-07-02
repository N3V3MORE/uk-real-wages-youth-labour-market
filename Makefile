PYTHON ?= python
PYTHONPATH := src
export PYTHONPATH

.PHONY: data clean analysis charts evidence dashboard test all

data:
	$(PYTHON) -m uk_wages.download

clean:
	$(PYTHON) -m uk_wages.clean_cpi
	$(PYTHON) -m uk_wages.clean_ashe
	$(PYTHON) -m uk_wages.clean_region_ashe
	$(PYTHON) -m uk_wages.clean_a05
	$(PYTHON) -m uk_wages.clean_earn01
	$(PYTHON) -m uk_wages.clean_rti
	$(PYTHON) -m uk_wages.ashe_decomposition
	$(PYTHON) -m uk_wages.ashe_quality
	$(PYTHON) -m uk_wages.ashe_composition
	$(PYTHON) -m uk_wages.minimum_wage

analysis:
	$(PYTHON) -m uk_wages.analysis
	$(PYTHON) -m uk_wages.rti_analysis

charts:
	$(PYTHON) -m uk_wages.charts

evidence:
	$(PYTHON) -m uk_wages.rti_triangulation
	$(PYTHON) -m uk_wages.robustness --run-all
	$(PYTHON) -m uk_wages.source_validation
	$(PYTHON) -m uk_wages.triangulation
	$(PYTHON) -m uk_wages.final_claims
	$(PYTHON) -m uk_wages.research_note
	$(PYTHON) -m uk_wages.claim_confidence
	$(PYTHON) -m uk_wages.robustness --contrarian
	$(PYTHON) -m uk_wages.lineage
	$(PYTHON) -m uk_wages.evidence --build-report

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

test:
	$(PYTHON) -m pytest

all: data clean analysis charts evidence test
