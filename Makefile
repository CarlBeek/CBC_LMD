install_test:
	pip install -r requirements.txt

test:
	pytest test_all.py

lint:
	mypy --follow-imports=silent --warn-unused-ignores --ignore-missing-imports --check-untyped-defs --disallow-incomplete-defs --disallow-untyped-defs --strict-optional -p cbc_lmd; \
	flake8 --max-line-length=120 cbc_lmd

visualise:
	python visualise_all.py
