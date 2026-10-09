"""The generator must format its output, or fail loudly.

``format_with_ruff`` used to swallow every failure and hand back the unformatted
source. That is how the committed example artifacts became reproducible only in an
environment that happened to have ruff installed: anywhere else, generation kept
unused imports and unstable whitespace without reporting anything.
"""
import shutil

import pytest

from protobuf_pydantic_gen import template_renderer
from protobuf_pydantic_gen.template_renderer import TemplateRenderer, get_ruff_path

UNFORMATTED = "import os\n\n\n\ndef f():\n    return 1\n"

ANNOTATED = "import os\nfrom typing import Optional\n\n\nclass A:\n    x: Optional[int] = None\n"
# Both imports are used, so the sample exercises code that survives `--select F401`.
LAYOUT_SENSITIVE = (
    "from google.protobuf import message as _message\n"
    "from protobuf_pydantic_gen.ext import pool\n\n\n"
    "def f(x: _message.Message) -> object:\n"
    "    return pool\n"
)


def test_ruff_is_available():
    """ruff is a declared dependency, so the generation environment must provide it."""
    assert shutil.which(get_ruff_path()), (
        "ruff must be installed — the generator formats generated code with it"
    )


def test_formatting_is_applied():
    formatted = TemplateRenderer().format_with_ruff(UNFORMATTED)

    # `ruff check --fix` drops the unused import; the header is normalised.
    assert "import os" not in formatted
    assert formatted == "def f():\n    return 1\n"



def test_annotations_are_not_modernised():
    """Ruff's default rule set rewrites `Optional[x]` to `x | None`, which moves the
    Python floor of the generated code; only unused-import cleanup may run."""
    formatted = TemplateRenderer().format_with_ruff(ANNOTATED)

    assert "Optional[int]" in formatted
    assert "from __future__ import annotations" not in formatted


def test_missing_formatter_fails_loudly(monkeypatch):
    monkeypatch.setattr(template_renderer, "get_ruff_path", lambda: "/nonexistent/ruff")

    with pytest.raises(RuntimeError) as excinfo:
        TemplateRenderer().format_with_ruff(UNFORMATTED)

    message = str(excinfo.value)
    assert "not found" in message
    assert "pip install ruff" in message


def test_formatter_failure_fails_loudly(monkeypatch):
    monkeypatch.setattr(template_renderer, "get_ruff_path", lambda: "false")

    with pytest.raises(RuntimeError) as excinfo:
        TemplateRenderer().format_with_ruff(UNFORMATTED)

    assert "failed" in str(excinfo.value)



def test_output_does_not_depend_on_the_working_directory(tmp_path, monkeypatch):
    """Import layout must not follow the project root: `ruff check --select I` would
    classify `protobuf_pydantic_gen` as first- or third-party depending on where
    generation runs, changing the generated files."""
    renderer = TemplateRenderer()
    expected = renderer.format_with_ruff(LAYOUT_SENSITIVE)

    monkeypatch.chdir(tmp_path)

    assert renderer.format_with_ruff(LAYOUT_SENSITIVE) == expected
