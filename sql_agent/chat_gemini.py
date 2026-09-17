"""
Gemini compatibility wrapper for legacy SQL agent scripts.
Provides get_model(), start_chat(), and send_message() interfaces
interfacing with the modern google-genai SDK and gemini_utils.
"""

import os
import sys
from pathlib import Path
from typing import Any, Iterator, Optional

# Ensure repository root is on sys.path for gemini_utils import
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    from gemini_utils import get_gemini_client
except ImportError:
    get_gemini_client = None


class GeminiResponseWrapper:
    """Wrapper matching the response object expected by legacy agent scripts."""

    def __init__(self, text: str):
        self.text = text

    def resolve(self) -> "GeminiResponseWrapper":
        """No-op to satisfy response.resolve() calls in legacy scripts."""
        return self


class GeminiStreamChunkWrapper:
    """Wrapper for streaming response chunks."""

    def __init__(self, text: str):
        self.text = text


class GeminiChatSession:
    """Wrapper providing start_chat session compatibility with google-genai."""

    def __init__(self, client: Any, model_name: str):
        self.client = client
        self.model_name = model_name

    def send_message(self, prompt: str, stream: bool = False) -> Any:
        """Send a message to Gemini and return either a response wrapper or a generator."""
        if self.client is None:
            raise RuntimeError(
                "Gemini client is not initialized. Ensure GOOGLE_API_KEY is set "
                "and google-genai is installed."
            )

        if stream:
            return self._stream_message(prompt)
        else:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = getattr(response, "text", "") or ""
            return GeminiResponseWrapper(text)

    def _stream_message(self, prompt: str) -> Iterator[GeminiStreamChunkWrapper]:
        """Stream chunks from generate_content_stream."""
        response_stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt
        )
        for chunk in response_stream:
            chunk_text = getattr(chunk, "text", "") or ""
            yield GeminiStreamChunkWrapper(chunk_text)


class GeminiModel:
    """Model wrapper providing start_chat() for legacy scripts."""

    def __init__(self, model_name: str = "gemini-2.5-flash", api_key_name: str = "GOOGLE_API_KEY"):
        self.model_name = model_name
        self.api_key_name = api_key_name
        self._client = None

    @property
    def client(self) -> Optional[Any]:
        """Lazy client initialization."""
        if self._client is None and get_gemini_client is not None:
            try:
                self._client = get_gemini_client(self.api_key_name)
            except Exception:
                self._client = None
        return self._client

    def start_chat(self) -> GeminiChatSession:
        """Start a chat session."""
        return GeminiChatSession(self.client, self.model_name)


def get_model(model_name: str = "gemini-2.5-flash", api_key_name: str = "GOOGLE_API_KEY") -> GeminiModel:
    """Return a model wrapper compatible with legacy agent.py and agent_v2.py."""
    return GeminiModel(model_name=model_name, api_key_name=api_key_name)

