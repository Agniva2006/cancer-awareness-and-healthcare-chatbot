.PHONY: install dev test lint fmt

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest

lint:
	flake8 app tests

fmt:
	black app tests scripts
