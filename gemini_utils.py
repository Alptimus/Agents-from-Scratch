"""
Gemini API utilities for orchestrator integration.

Provides helper functions for initializing Gemini client and making API calls.
"""

import os
from typing import Any

try:
    from google import genai
    from google.genai.types import GenerateContentConfig, HarmCategory, HarmBlockThreshold, SafetySetting
except ImportError as exc:  # pragma: no cover - exercised through import isolation tests
    genai = None
    GenerateContentConfig = None
    HarmCategory = None
    HarmBlockThreshold = None
    SafetySetting = None
    GEMINI_IMPORT_ERROR = exc
else:
    GEMINI_IMPORT_ERROR = None

try:
    from decouple import config
except ImportError:  # pragma: no cover - fallback when dependency is absent
    def config(name: str, default: Any = None) -> Any:
        return os.environ.get(name, default)


def _require_gemini_dependencies() -> None:
    """Raise an actionable error when the Gemini SDK is unavailable."""
    if genai is None:
        raise RuntimeError(
            "Gemini support requires google-genai. Install project dependencies with: "
            "pip install -r requirements.txt"
        ) from GEMINI_IMPORT_ERROR


def get_gemini_client(api_key_name: str = "GOOGLE_API_KEY") -> Any:
    """
    Initialize and return a Google Gemini client.

    Args:
        api_key_name: Environment variable name containing the API key (default: GOOGLE_API_KEY)

    Returns:
        Initialized genai.Client instance

    Raises:
        ValueError: If API key is not found in environment
    """
    _require_gemini_dependencies()
    api_key = config(api_key_name, default=None)
    if not api_key:
        raise ValueError(
            f"API key '{api_key_name}' not found in environment. "
            "Set it in .env file or environment variables."
        )
    return genai.Client(api_key=api_key)


def call_gemini(client: Any, prompt: str, model: str = "gemini-2.5-flash") -> str:
    """
    Call Gemini API with a prompt and return the response text.

    Args:
        client: Initialized Gemini client
        prompt: The prompt to send to Gemini
        model: Model name to use (default: gemini-2.5-flash)

    Returns:
        Response text from Gemini

    Raises:
        Exception: If API call fails
    """
    _require_gemini_dependencies()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=GenerateContentConfig(
            safety_settings=[
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold.BLOCK_NONE
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold.BLOCK_NONE
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold.BLOCK_NONE
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold.BLOCK_NONE
                )
            ]
        )
    )
    return response.text.strip()
