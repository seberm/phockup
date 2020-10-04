.PHONY: all help clean test pip version tox venv venv-clean

TOX=tox

PROJECT_NAME=phockup

PIPENV_BIN=/usr/bin/pipenv
GIT_CURRENT_BRANCH=$(shell git rev-parse --abbrev-ref HEAD)

help:
	@echo "Usage notes:"
	@echo "make test - Run unit tests using TOX."
	@echo "make version - Print $(PROJECT_NAME)'s version."
	@echo "make clean - Clean working files from the repository."
	@echo "make venv - Create and prepare python virtual environment using the pipenv."

all: help

clean:
	rm -rf rpms build dist $(PROJECT_NAME).egg-info
	rm -rf .mypy_cache .pytest_cache .tox
	-find . -type f -name "*.pyc" -exec rm -f {} \;
	-find . -type d -name "__pycache__" -exec rm -rf {} \;
	#cd tests && $(MAKE) clean

tox:
	$(TOX)

test: tox

version:
	@python3 <<< 'from $(PROJECT_NAME) import __version__ as VERSION; print(VERSION)'
	@python3 <<< 'from $(PROJECT_NAME) import __git_version__ as GIT_VERSION; print(GIT_VERSION)'

pip:
	python3 setup.py sdist

venv:
	$(PIPENV_BIN) install
	$(PIPENV_BIN) shell

venv-clean:
	-$(PIPENV_BIN) --rm
