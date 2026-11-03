PYTHON := .venv/bin/python
PIP := .venv/bin/pip
STREAMLIT := .venv/bin/python -m streamlit

.PHONY: venv install analyze export test lint run diagnostics clean

venv:
	python3 -m venv .venv

config/settings.yaml: config/settings.example.yaml
	cp $< $@

install: venv config/settings.yaml
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

analyze: install
	$(PYTHON) main.py analyze --repo all

export: analyze
	$(PYTHON) main.py export --all

test: install
	$(PYTHON) -m pytest -q

lint: install
	$(PYTHON) -m ruff check .

run: export
	$(STREAMLIT) run app.py

diagnostics: install
	$(PYTHON) main.py diagnostics

clean:
	rm -rf .pytest_cache .ruff_cache
