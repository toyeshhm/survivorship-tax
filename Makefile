# Deterministic by construction: single-threaded BLAS and a fixed hash seed, so
# `make all` twice in a clean checkout produces a byte-identical results/ tree.
export PYTHONHASHSEED := 0
export OMP_NUM_THREADS := 1
export OPENBLAS_NUM_THREADS := 1
export MKL_NUM_THREADS := 1

PY := .venv/bin/python

.PHONY: help setup lint typecheck test check data research export web all clean

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n",$$1,$$2}'

setup:  ## create the venv and install everything
	uv venv --python 3.12
	uv pip install --python $(PY) -e ".[dev]"

lint:  ## ruff
	$(PY) -m ruff check src tests scripts
	$(PY) -m ruff format --check src tests scripts

typecheck:  ## mypy --strict
	$(PY) -m mypy

test:  ## pytest
	$(PY) -m pytest

check: lint typecheck test  ## lint, typecheck, test

data:  ## fetch prices, membership, and factors
	$(PY) scripts/fetch_prices.py

research:  ## run the full study and write results/
	$(PY) scripts/run_research.py

export:  ## write dashboard JSON from results/
	$(PY) scripts/export_web.py

web:  ## build the static dashboard
	cd web && npm ci && npm run build

all: check data research export web  ## everything, in order

clean:
	rm -rf results/*.json results/*.csv results/*.parquet web/.next web/out
