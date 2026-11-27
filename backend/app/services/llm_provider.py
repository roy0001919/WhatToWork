from google import genai

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


llm_provider = LLMProvider()
