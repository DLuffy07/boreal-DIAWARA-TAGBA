PY ?= python

.PHONY: all ingest core reload dashboard

all:        ## pipeline complet
	$(PY) pipeline.py all

ingest:     ## sources -> raw (+ journal d'ingestion)
	$(PY) pipeline.py ingest

core:       ## raw -> core
	$(PY) pipeline.py core

reload:     ## rejoue un mois, ex. make reload MONTH=2024_03
	$(PY) pipeline.py reload --month $(MONTH)

dashboard:
	streamlit run dashboard/app.py
