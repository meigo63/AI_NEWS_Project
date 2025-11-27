"""Utility helpers used by the Flask app.

Provides small, dependency-free helpers for text cleaning and file-reading so
frontend + tests can function while the ML pieces are built.
"""

import re
from typing import Optional


def clean_text(text: str) -> str:
    """Perform lightweight cleaning on article text.

    This function keeps things simple and deterministic: trims whitespace,
    collapses multiple spaces, and removes non-printable control characters.
    """
    if not isinstance(text, str):
        return ""

    # Normalize line breaks and whitespace
    text = text.strip()
    text = re.sub(r"\s+", " ", text)

    # Remove control characters
    text = re.sub(r"[\x00-\x1f\x7f]+", "", text)
    return text


def read_text_file(file_storage) -> Optional[str]:
    """Read file content from a Flask FileStorage object.

    Supports plain .txt files for now. PDFs are accepted but not parsed — this
    returns a helpful placeholder message. The function never relies on heavy
    external libraries so the app remains lightweight.
    """
    filename = getattr(file_storage, "filename", "")
    if not filename:
        return None

    lower = filename.lower()
    try:
        if lower.endswith(".txt"):
            raw = file_storage.stream.read()
            # Flask FileStorage returns bytes — decode safely
            try:
                text = raw.decode("utf-8")
            except Exception:
                text = raw.decode("latin-1", errors="ignore")
            return clean_text(text)

        # PDF handling is intentionally a placeholder to avoid PDF libs here
        if lower.endswith(".pdf"):
            return (
                "[PDF upload accepted] — PDF parsing is a placeholder in this demo."
                " Integrate a library like PyPDF2 or pdfplumber later to read PDFs."
            )

    except Exception:
        return None

    return None
