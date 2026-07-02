PYTHON ?= python
PYTHONPATH := src
export PYTHONPATH

.PHONY: data clean analysis charts dashboard test all

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

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

test:
	$(PYTHON) -m pytest

all: data clean analysis charts test
