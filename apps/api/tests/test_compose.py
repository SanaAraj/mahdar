from pathlib import Path

import yaml

from app import constants

_COMPOSE_PATH = Path(__file__).resolve().parents[3] / "docker-compose.yml"


def _ollama_command() -> str:
    services = yaml.safe_load(_COMPOSE_PATH.read_text(encoding="utf-8"))["services"]
    command = services["ollama"]["command"]
    return "\n".join(command) if isinstance(command, list) else str(command)


def test_ollama_model_reference_has_no_shell_escape():
    command = _ollama_command()
    assert "LOCAL_LLM_MODEL" in command
    assert "$$" not in command


def test_ollama_model_default_matches_the_app_default():

    expected = f"${{LOCAL_LLM_MODEL:-{constants.DEFAULT_LOCAL_LLM_MODEL}}}"
    assert expected in _ollama_command()
