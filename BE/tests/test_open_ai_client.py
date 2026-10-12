"""Calls the real OpenAI API. API tests are skipped unless OPENAI_API_KEY is set in .env."""
#pytest tests/test_open_ai_client.py -v -s
import openai
import pytest

from app.config import Settings
from app.errors import OpenAIClientError
from app.service.open_ai_client import OpenAIClient

settings = Settings()

live = pytest.mark.skipif(not settings.openai_api_key, reason="OPENAI_API_KEY is not set in .env")


@pytest.fixture
async def make_client():
    clients = []

    def make(sdk: openai.AsyncOpenAI | None = None, **overrides):
        client = OpenAIClient(settings.model_copy(update=overrides), sdk)
        clients.append(client)
        return client

    yield make
    for client in clients:
        await client.client.close()


@live
async def test_generate_with_system_prompt_and_model(make_client):
    answer = await make_client().generate(
        user_prompt="hello",
        system_prompt="Whatever the user says, reply with exactly the single word: pong",
        model=settings.openai_model,
    )
    print(f"\nOpenAI answer: {answer!r}")

    assert "pong" in answer.lower()


@live
async def test_generate_defaults_to_settings_model(make_client):
    answer = await make_client().generate("Reply with the single word: pong")
    print(f"\nOpenAI answer: {answer!r}")

    assert "pong" in answer.lower()


@live
async def test_unknown_model_raises(make_client):
    with pytest.raises(OpenAIClientError, match="OpenAI HTTP 4") as exc_info:
        await make_client().generate("hi", model="model-that-does-not-exist")
    print(f"\nOpenAI error: {exc_info.value}")


@live
async def test_invalid_api_key_raises_without_leaking_it(make_client):
    bad_key = "sk-invalid-key-for-test"

    with pytest.raises(OpenAIClientError, match="OpenAI HTTP 401") as exc_info:
        await make_client(openai_api_key=bad_key).generate("hi")
    print(f"\nOpenAI error: {exc_info.value}")

    assert bad_key not in str(exc_info.value)


async def test_network_error_raises(make_client):
    # Nothing listens on port 9, so the real HTTP connection is refused.
    sdk = openai.AsyncOpenAI(api_key="sk-unused", base_url="http://127.0.0.1:9", max_retries=0)

    with pytest.raises(OpenAIClientError, match="Cannot reach OpenAI"):
        await make_client(sdk, openai_api_key="sk-unused").generate("hi")


def test_missing_api_key_rejected():
    with pytest.raises(OpenAIClientError, match="OPENAI_API_KEY must be set"):
        OpenAIClient(settings.model_copy(update={"openai_api_key": None}))
