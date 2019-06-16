install_test:
	pip install -r requirements.txt

test:
	pytest test_all.py

visualise:
	python visualisations/tree_visualiser.py