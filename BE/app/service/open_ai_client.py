import openai

from app.config import Settings
from app.errors import OpenAIClientError


class OpenAIClient:
    """Generates text answers through the OpenAI Responses API."""

    def __init__(self, settings: Settings, client: openai.AsyncOpenAI | None = None):
        if not settings.openai_api_key:
            raise OpenAIClientError("OPENAI_API_KEY must be set")
        self.model = settings.openai_model
        self.client = client or openai.AsyncOpenAI(
            api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds
        )

    async def generate(
        self, user_prompt: str, system_prompt: str | None = None, model: str | None = None
    ) -> str:
        """`model` falls back to OPENAI_MODEL when not given."""
        try:
            response = await self.client.responses.create(
                model=model or self.model,
                instructions=system_prompt or openai.omit,
                input=user_prompt,
            )
        except openai.APIStatusError as exc:
            raise OpenAIClientError(f"OpenAI HTTP {exc.status_code}: {exc.message}") from exc
        except openai.APIConnectionError as exc:
            raise OpenAIClientError("Cannot reach OpenAI (network error or timeout)") from exc

        if not response.output_text:
            raise OpenAIClientError("OpenAI returned an empty answer")
        return response.output_text
