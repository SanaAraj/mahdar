from app import constants
from app.features.analysis import prompts
from app.shared.errors import AnalysisError
from app.shared.models import Sentence

_LINE_SURROGATE_CHARS: int = 30


def sentence_estimated_tokens(sentence: Sentence) -> int:

    return prompts.estimate_tokens(sentence.text) + prompts.estimate_tokens(
        "x" * _LINE_SURROGATE_CHARS
    )


def split_into_windows(
    sentences: list[Sentence], budget: int | None = None
) -> list[list[Sentence]]:

    if budget is None:
        budget = constants.WINDOW_TOKEN_BUDGET
    windows: list[list[Sentence]] = []
    current: list[Sentence] = []
    used = 0
    for sentence in sentences:
        estimate = sentence_estimated_tokens(sentence)
        if estimate > budget:
            raise AnalysisError(
                "analysis.too_long",
                f"sentence {sentence.id} ~{estimate} tokens exceeds window budget {budget}",
            )
        if current and used + estimate > budget:
            windows.append(current)
            current = []
            used = 0
        current.append(sentence)
        used += estimate
    if current:
        windows.append(current)
    return windows
