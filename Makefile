help:					# List all make commands
	@awk -F ':.*#' '/^[a-zA-Z_-]+:.*?#/ { printf "\033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort

lint:					# Run linter commands
	autoflake --in-place --recursive --remove-unused-variables --remove-all-unused-imports --exclude docker/,.git/,.local .
	isort --skip .local --skip migrations --skip wsgi --skip asgi --line-length 120 --multi-line VERTICAL_HANGING_INDENT --trailing-comma .
	black --exclude '(.local/|docker/|migrations/|config/settings\.py|manage\.py|\.direnv|\.eggs|\.git|\.hg|\.mypy_cache|\.nox|\.tox|\.venv|venv|\.svn|\.ipynb_checkpoints|_build|buck-out|build|dist|__pypackages__)' -l 120 .
	flake8 --config setup.cfg

test:					# Execute `pytest` and coverage report
	./scripts/cleanup.sh
	PYTHONPATH=. coverage run --include="pydokku/*" -m pytest -vvvs $(TEST_ARGS)
	coverage report

test-x:					# Execute `pytest` with `-x` option and coverage report
	./scripts/cleanup.sh
	PYTHONPATH=. coverage run --include="pydokku/*" -m pytest -vvvsx $(TEST_ARGS)
	coverage report

type-check:				# Run mypy in the project
	mypy pydokku/ tests/

vm-create:				# Create a virtual machine using libvirt/virsh to make isolated tests easier (requires sudo)
	@sudo ./scripts/vm.sh create

vm-delete:				# Delete the virtual machine, its disk and shared folder (requires sudo)
	@sudo ./scripts/vm.sh delete

vm-ip:					# Prints the virtual machine local IP address
	@./scripts/vm.sh ip

vm-ssh:					# Executes command to log-in into the virtual machine using SSH
	@./scripts/vm.sh ssh

vm-start:				# Starts the virtual machine and waits for it to be turned on
	@./scripts/vm.sh start

vm-stop:				# Sends the shutdown signal to the virtual machine and wait for it to be turned off
	@./scripts/vm.sh stop

.PHONY: help lint test test-x type-check vm-create vm-delete vm-ip vm-ssh vm-start vm-stop
