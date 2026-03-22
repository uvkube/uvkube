# uvkube

Kubernetes infrastructure management CLI for Hetzner Cloud, built with Python.

## Stack
- Python 3.12, uv for package management
- Typer (CLI), Rich (terminal output), Pydantic v2 (config validation)
- hcloud SDK (Hetzner Cloud API)
- Ansible (k3s bootstrap via playbooks)
- FastAPI (future dashboard)
- pytest, ruff, mypy, taskipy

## Structure
- `src/uvkube/` — source code
- `src/uvkube/commands/` — CLI commands (infra.py)
- `src/uvkube/providers/` — cloud providers (hetzner.py, in_memory.py)
- `src/uvkube/config/` — Pydantic models
- `src/uvkube/ansible/` — runner, inventory, playbooks
- `tests/` — mirrors src structure

## Commands
- `uv run task check` — lint + types + tests
- `uv run task test` — tests only
- `uv run task lint` — ruff
- `uv run task types` — mypy
- `uv run uvkube infra --help` — CLI

## Current state
- `uvkube infra init/up/bootstrap/firewall/status/destroy` all working
- Provisions real Hetzner servers, bootstraps k3s with Ansible
- Tested end to end — nginx and FastAPI both served from cluster

## Next steps
- FastAPI dashboard
- `uvkube app deploy` command
- PyPI publish