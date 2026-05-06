.PHONY: help machine-install machine-dev-backend machine-dev-frontend machine-test machine-compile machine-build machine-check

MACHINE_APP_DIR := machine-process-visibility-poc

help:
	@echo "Targets:"
	@echo "  make machine-install       Install machine-process PoC dependencies"
	@echo "  make machine-dev-backend   Start machine-process backend"
	@echo "  make machine-dev-frontend  Start machine-process frontend"
	@echo "  make machine-test          Run machine-process backend tests"
	@echo "  make machine-build         Build machine-process frontend"
	@echo "  make machine-check         Run machine-process validation"

machine-install:
	$(MAKE) -C $(MACHINE_APP_DIR) install

machine-dev-backend:
	$(MAKE) -C $(MACHINE_APP_DIR) dev-backend

machine-dev-frontend:
	$(MAKE) -C $(MACHINE_APP_DIR) dev-frontend

machine-test:
	$(MAKE) -C $(MACHINE_APP_DIR) test

machine-compile:
	$(MAKE) -C $(MACHINE_APP_DIR) compile

machine-build:
	$(MAKE) -C $(MACHINE_APP_DIR) build

machine-check:
	$(MAKE) -C $(MACHINE_APP_DIR) check
