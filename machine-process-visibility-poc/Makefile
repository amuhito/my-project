.PHONY: help setup-backend setup-frontend install dev-backend dev-frontend test compile build check

SYSTEM_PYTHON ?= python3
PYTHON ?= .venv/bin/python

help:
	@echo "Targets:"
	@echo "  make setup-backend   Create .venv and install backend dependencies"
	@echo "  make setup-frontend  Install frontend dependencies"
	@echo "  make install         Install backend and frontend dependencies"
	@echo "  make dev-backend     Start FastAPI backend"
	@echo "  make dev-frontend    Start Vite frontend"
	@echo "  make test            Run backend tests"
	@echo "  make build           Build frontend"
	@echo "  make check           Run test, compile, and build"

setup-backend:
	$(SYSTEM_PYTHON) -m venv .venv
	.venv/bin/python -m pip install -r backend/requirements.txt

setup-frontend:
	npm install

install: setup-backend setup-frontend

dev-backend:
	$(PYTHON) backend/main.py

dev-frontend:
	npm run dev

test:
	$(PYTHON) -m pytest backend/tests

compile:
	$(PYTHON) -m compileall backend

build:
	npm run build

check: test compile build
