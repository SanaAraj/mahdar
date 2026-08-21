"""Static checks on docker-compose.yml: the ollama service's model reference.

Regression: the command once escaped the variable as $${LOCAL_LLM_MODEL:-...},
deferring resolution to the in-container shell, where the variable is never
set, so the service always pulled the default model while the app requested
the .env override. Compose must interpolate it at parse time instead.
"""

from pathlib import Path

import yaml

from backend.app import constants

_COMPOSE_PATH = Path(__file__).resolve().parents[1] / "docker-compose.yml"


def _ollama_command() -> str:
    services = yaml.safe_load(_COMPOSE_PATH.read_text(encoding="utf-8"))["services"]
    command = services["ollama"]["command"]
    return "\n".join(command) if isinstance(command, list) else str(command)


def test_ollama_model_reference_has_no_shell_escape():
    command = _ollama_command()
    assert "LOCAL_LLM_MODEL" in command
    assert "$$" not in command


def test_ollama_model_default_matches_the_app_default():
    # Both sides must fall back to the same model when .env sets no override.
    expected = f"${{LOCAL_LLM_MODEL:-{constants.DEFAULT_LOCAL_LLM_MODEL}}}"
    assert expected in _ollama_command()
