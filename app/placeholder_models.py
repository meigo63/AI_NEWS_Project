"""Placeholder model functions for future ML integration.

These functions are lightweight placeholders that *do not* load or require
any machine learning models. They return deterministic sample outputs and
JSON-friendly dictionaries so the web app can be developed and tested while
models are trained separately.

Do NOT modify these to import real models until you're ready to integrate
trained files — this file is intentionally free of heavy dependencies.
"""

from typing import Dict


def classify_article(text: str) -> Dict[str, str]:
    """Return a placeholder classification result.

    Args:
        text: The article text (ignored by dummy function).

    Returns:
        A dictionary with sample shape for future real model output.
    """
    return {
        "category": "N/A",
        "confidence": "N/A",
        "note": "Model not available yet — placeholder result."
    }


def detect_fake_news(text: str) -> Dict[str, str]:
    """Return a placeholder fake/real detection result.

    Args:
        text: The article text (ignored by dummy function).

    Returns:
        A dictionary mimicking a classifier + an explainability field.
    """
    return {
        "status": "Model pending",
        "fake_or_real": "N/A",
        "explanation": "Model not integrated yet — explainability will be available later (LIME/SHAP)."
    }
