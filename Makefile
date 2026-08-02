SHELL := /usr/bin/env bash

VENV ?= .venv
VENV_PY := $(VENV)/bin/python

CLI_ARGS :=
ifneq ($(strip $(CONFIG)),)
CLI_ARGS += -c "$(CONFIG)"
endif
ifneq ($(strip $(PLUGIN)),)
CLI_ARGS += -p "$(PLUGIN)"
endif
ifneq ($(strip $(PLUGIN_URL)),)
CLI_ARGS += -u "$(PLUGIN_URL)"
endif
ifneq ($(strip $(QUERY)),)
CLI_ARGS += -q "$(QUERY)"
endif
ifeq ($(strip $(PLUGIN_MANAGER)),1)
CLI_ARGS += -i
endif
ifneq ($(strip $(EXTRA_ARGS)),)
CLI_ARGS += $(EXTRA_ARGS)
endif

.PHONY: help setup playwright run themes

help:
	@echo "Targets:"
	@echo "  make run CONFIG=./config2.json"
	@echo "  make run PLUGIN=./path/to/plugin QUERY=test"
	@echo "  make run PLUGIN_URL=https://example.com/plugin.zip QUERY=test"
	@echo "  make run PLUGIN_MANAGER=1 PLUGIN=./path/to/plugin"
	@echo "  make run CONFIG=./config2.json SKIP_PLAYWRIGHT=1"
	@echo "  make run EXTRA_ARGS='-c ./config2.json'"
	@echo
	@echo "Variables:"
	@echo "  VENV=.venv"
	@echo "  CONFIG, PLUGIN, PLUGIN_URL, QUERY, PLUGIN_MANAGER=1, SKIP_PLAYWRIGHT=1, EXTRA_ARGS"

setup:
	@if [ -x "$(VENV_PY)" ]; then \
		echo "Existing virtual environment detected; syncing dependencies."; \
	else \
		echo "Creating virtual environment at $(VENV)"; \
		uv venv "$(VENV)"; \
	fi
	@uv pip install -e . --group dev -p "$(VENV_PY)"

playwright: setup
	@if [ "$(SKIP_PLAYWRIGHT)" = "1" ]; then \
		echo "Skipping Playwright install."; \
	else \
		echo "Installing Playwright Chromium (headless)..."; \
		if ! "$(VENV_PY)" -m playwright install chromium; then \
			echo "Playwright install failed; attempting elevated install-deps via sudo..."; \
			if command -v sudo >/dev/null 2>&1; then \
				sudo "$(VENV_PY)" -m playwright install-deps chromium; \
				"$(VENV_PY)" -m playwright install chromium; \
			else \
				echo "sudo is unavailable. Please install system deps manually and retry."; \
				exit 1; \
			fi; \
		fi; \
	fi

run: playwright
	@echo "Running web-render"
	@"$(VENV)/bin/web-render" $(CLI_ARGS)

themes: setup
	@echo "Converting Flow Launcher themes..."
	@"$(VENV_PY)" -m web_render.convert_themes
