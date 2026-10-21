PY ?= python
DB ?= boreal.duckdb

.PHONY: all ingest prep quality core test marts dashboard reload clean

all: ingest prep quality core test marts   ## pipeline complet

ingest:      ## A : sources -> raw (+ journal d'ingestion)
	@echo "TODO ingest" # $(PY) -m ingestion.load_raw --db $(DB)

prep:        ## A : raw -> prep (typage, normalisation)
	@echo "TODO prep"

quality:     ## A : règles qualité -> quarantaine
	@echo "TODO quality"

core:        ## A : prep -> core (schéma en étoile)
	@echo "TODO core"

test:        ## A : tests bloquants (un échec arrête make all)
	@echo "TODO test" # $(PY) -m pytest -q tests

marts:       ## B : core -> marts
	@echo "TODO marts"

dashboard:   ## B : lance le dashboard
	@echo "TODO dashboard" # streamlit run dashboard/app.py

reload:      ## A : rejoue un mois, ex. make reload MONTH=2024_03
	@test -n "$(MONTH)" || (echo "Usage : make reload MONTH=AAAA_MM" && exit 1)
	@echo "TODO reload $(MONTH)"

clean:
	rm -f $(DB)
