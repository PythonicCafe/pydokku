help:					# List all make commands
	@awk -F ':.*#' '/^[a-zA-Z_-]+:.*?#/ { printf "\033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort

lint:					# Run linter commands
	autoflake --in-place --recursive --remove-unused-variables --remove-all-unused-imports --exclude docker/,.git/,.local .
	isort --skip .local --skip migrations --skip wsgi --skip asgi --line-length 120 --multi-line VERTICAL_HANGING_INDENT --trailing-comma .
	black --exclude '(.local/|docker/|migrations/|config/settings\.py|manage\.py|\.direnv|\.eggs|\.git|\.hg|\.mypy_cache|\.nox|\.tox|\.venv|venv|\.svn|\.ipynb_checkpoints|_build|buck-out|build|dist|__pypackages__)' -l 120 .
	flake8 --config setup.cfg

test:					# Execute `pytest`
	./scripts/cleanup.sh
	PYTHONPATH=. pytest -x

test-v:					# Execute `pytest` with verbose option
	./scripts/cleanup.sh
	PYTHONPATH=. pytest -xvvv

.PHONY: help lint test test-v
