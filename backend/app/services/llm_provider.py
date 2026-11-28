from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings


class LLMProvider:
    """
    Unified LLM provider.

    Current provider: Google Gemini
    Future providers can implement the same interface.
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            api_key = settings.gemini_api_key

            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not configured."
                )

            self._client = genai.Client(
                api_key=api_key.strip()
            )

        return self._client

    def generate_text(
        self,
        prompt: str,
        model: str | None = None,
    ) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        client = self._get_client()

        response = client.models.generate_content(
            model=model or settings.gemini_model,
            contents=prompt,
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        return response.text.strip()

    def generate_content(
        self,
        contents: Any,
        config: types.GenerateContentConfig | None = None,
        model: str | None = None,
    ):
        """
        Generate Gemini content and return the complete response.

        Unlike generate_text(), this method preserves function calls,
        candidate contents, and other response metadata.
        """
        if contents is None:
            raise ValueError("Contents cannot be empty.")

        client = self._get_client()

        response = client.models.generate_content(
            model=model or settings.gemini_model,
            contents=contents,
            config=config,
        )

        if response is None:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        return response


llm_provider = LLMProvider()
