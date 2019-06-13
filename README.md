# Fast CBC LMD

Make it fast, please!

## To Run:

Set up a python 3 virtual environment, and then run the command:

~~~~
pip install -r requirements.txt
pytest test_all.py
~~~~

## Linter:

~~~~
mypy --follow-imports=silent --warn-unused-ignores --ignore-missing-imports --check-untyped-defs --disallow-incomplete-defs --disallow-untyped-defs --strict-optional -p cbc_lmd
~~~~
