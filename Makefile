.RECIPEPREFIX := >

PYTHON ?= python3
API_HOST ?= 0.0.0.0
API_PORT ?= 8000

.PHONY: help install test verify run smoke status tree clean-runtime

help:
>@echo "Enterprise Analyst AI Stack Lab"
>@echo ""
>@echo "Available commands:"
>@echo "  make install        Install Python dependencies"
>@echo "  make test           Run automated tests"
>@echo "  make verify         Run tests and generate Phase 1 evidence"
>@echo "  make run            Start the FastAPI development server"
>@echo "  make smoke          Run the HTTP smoke test"
>@echo "  make status         Show repository status"
>@echo "  make tree           Show repository structure"
>@echo "  make clean-runtime  Remove generated local runtime evidence"

install:
>$(PYTHON) -m pip install -r requirements.txt

test:
>$(PYTHON) -m pytest -q

verify:
>$(PYTHON) scripts/phase_1_verify.py

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
