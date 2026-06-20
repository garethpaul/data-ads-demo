PYTHON ?= python3
ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

.PHONY: check mutations

check:
	cd "$(ROOT)" && $(PYTHON) -m unittest discover -s tests -p 'test_*.py'
	cd "$(ROOT)" && $(PYTHON) -m py_compile home/ads_protocol.py tests/test_ads_protocol.py tests/test_integration_contracts.py
	cd "$(ROOT)" && git diff --check

mutations:
	cd "$(ROOT)" && $(PYTHON) scripts/test_mutations.py
