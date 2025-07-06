.PHONY: help install migrate run test clean

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make migrate    - Run database migrations"
	@echo "  make run        - Run development server"
	@echo "  make worker     - Run Celery worker"
	@echo "  make beat       - Run Celery beat"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean cache files"

install:
	uv venv .venv
	. .venv/bin/activate && uv pip install -e .

migrate:
	python manage.py makemigrations
	python manage.py migrate

run:
	python manage.py runserver

worker:
	celery -A config worker -l info

beat:
	celery -A config beat -l info

test:
	pytest

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf .coverage htmlcov/