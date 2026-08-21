"""Split a transcript into consecutive analysis windows of whole sentences.

A sentence is the atomic unit: a window never starts or ends inside one, so
the extractor always reads complete, ordered context. Each window is sized so
its transcript text (each sentence formatted as it appears in the prompt)
estimates at or under WINDOW_TOKEN_BUDGET, keeping window plus the shared
system prompt under MAX_PROMPT_TOKENS with margin for the corrective retry and
the reply. Sentence ids stay untouched across windows so the merged items cite
the real transcript line a milestone rests on.
"""

from app import constants
from app.core.errors import AnalysisError
from app.core.models import Sentence
from app.providers import prompts

# A close facsimile of the prompt's sentence line length: the id square, the
# speaker label with its timestamp, the separator spaces, and the newline.
_LINE_SURROGATE_CHARS: int = 30


def sentence_estimated_tokens(sentence: Sentence) -> int:
    """Token estimate of one formatted transcript line: its text plus overhead."""
    return prompts.estimate_tokens(sentence.text) + prompts.estimate_tokens(
        "x" * _LINE_SURROGATE_CHARS
    )


def split_into_windows(
    sentences: list[Sentence], budget: int | None = None
) -> list[list[Sentence]]:
    """Group consecutive sentences into windows, each under the token budget.

    Runs greedily, closing a window before the estimate crosses the budget.
    A single sentence that alone exceeds the budget cannot be split further,
    so it raises the same budget message a too-long reduce input would. Budget
    defaults to WINDOW_TOKEN_BUDGET and is read at call time so tests can narrow
    it without touching module state.
    """
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
