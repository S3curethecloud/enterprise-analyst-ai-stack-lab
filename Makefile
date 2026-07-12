.RECIPEPREFIX := >

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
API_HOST ?= 0.0.0.0
API_PORT ?= 8000

.PHONY: help install test verify verify-phase1 verify-phase2 verify-phase3 run smoke status tree clean-runtime

help:
>@echo "Enterprise Analyst AI Stack Lab"
>@echo ""
>@echo "Available commands:"
>@echo "  make install        Install Python dependencies"
>@echo "  make test           Run automated tests"
>@echo "  make verify         Run the current Phase 3 verification gate"
>@echo "  make verify-phase1  Generate Phase 1 evidence"
>@echo "  make verify-phase2  Generate Phase 2 evidence"
>@echo "  make verify-phase3  Generate Phase 3 evidence"
>@echo "  make run            Start the FastAPI development server"
>@echo "  make smoke          Run the HTTP smoke test"
>@echo "  make status         Show repository status"
>@echo "  make tree           Show repository structure"
>@echo "  make clean-runtime  Remove generated local runtime evidence"

install:
>$(PYTHON) -m pip install -r requirements.txt

test:
>$(PYTHON) -m pytest -q

verify: verify-phase3

verify-phase1:
>$(PYTHON) scripts/phase_1_verify.py

verify-phase2:
>$(PYTHON) scripts/phase_2_verify.py

run:
>$(PYTHON) -m uvicorn apps.api.app.main:app --host $(API_HOST) --port $(API_PORT) --reload

smoke:
>./scripts/smoke_test.sh

status:
>git status --short
>git log -1 --oneline

tree:
>find . -maxdepth 3 -type d -not -path "./.git*" -not -path "./.venv*" -not -path "./__pycache__*" | sort

clean-runtime:
>find evidence/traces -type f ! -name ".gitkeep" -delete
>find evidence/policy-decisions -type f ! -name ".gitkeep" -delete

verify-phase3:
>$(PYTHON) scripts/phase_3_verify.py
