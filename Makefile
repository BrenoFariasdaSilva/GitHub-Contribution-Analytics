ifeq ($(OS),Windows_NT)
PYTHON ?= py -3
VENV_PYTHON := .venv/Scripts/python.exe
else
PYTHON ?= python3
VENV_PYTHON := .venv/bin/python
endif

.PHONY: check-git install-git ensure-git venv install analyze export test lint run diagnostics clean

check-git:
	$(PYTHON) scripts/project_setup.py check-git

install-git ensure-git:
	$(PYTHON) scripts/project_setup.py ensure-git

venv:
	$(PYTHON) -m venv .venv

config/settings.yaml: config/settings.example.yaml
	$(PYTHON) scripts/project_setup.py config

install: ensure-git venv config/settings.yaml
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt

analyze: install
	$(PYTHON) scripts/project_setup.py run $(VENV_PYTHON) main.py analyze --repo all

export: analyze
	$(PYTHON) scripts/project_setup.py run $(VENV_PYTHON) main.py export --all

test: install
	$(PYTHON) scripts/project_setup.py run $(VENV_PYTHON) -m pytest -q

lint: install
	$(PYTHON) scripts/project_setup.py run $(VENV_PYTHON) -m ruff check .

run: export
	$(PYTHON) scripts/project_setup.py run $(VENV_PYTHON) -m streamlit run app.py

diagnostics: install
	$(PYTHON) scripts/project_setup.py run $(VENV_PYTHON) main.py diagnostics

clean:
	$(PYTHON) scripts/project_setup.py clean
