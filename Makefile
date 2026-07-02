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

analysis:
	$(PYTHON) -m uk_wages.analysis

charts:
	$(PYTHON) -m uk_wages.charts

evidence:
	$(PYTHON) -m uk_wages.robustness --run-all
	$(PYTHON) -m uk_wages.source_validation
	$(PYTHON) -m uk_wages.triangulation
	$(PYTHON) -m uk_wages.final_claims
	$(PYTHON) -m uk_wages.robustness --contrarian
	$(PYTHON) -m uk_wages.evidence --build-report

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

test:
	$(PYTHON) -m pytest

all: data clean analysis charts evidence test
