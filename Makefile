.PHONY: install test run compare app
install:
	pip install -e ".[dev,app]"
test:
	pytest -q
run:
	extracteval run tasks/invoices.yaml
compare:
	extracteval compare tasks/invoices.yaml --providers mock
app:
	streamlit run src/extracteval/app.py
