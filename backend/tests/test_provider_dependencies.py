"""The provider packages ``init_chat_model`` needs must be installed.

Each provider string maps to an optional LangChain integration package. A
missing package only shows up when something asks for that provider, so these
tests construct a model (no network call) for each supported provider.
"""

import pytest
from langchain.chat_models import init_chat_model


@pytest.mark.parametrize(
    ("model", "expected_class"),
    [
        ("openai:gpt-4.1", "ChatOpenAI"),
        ("ollama:llama3.1", "ChatOllama"),
        ("google_genai:gemini-2.5-flash", "ChatGoogleGenerativeAI"),
    ],
)
def test_supported_provider_builds(
    monkeypatch: pytest.MonkeyPatch,
    model: str,
    expected_class: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    llm = init_chat_model(model, temperature=0.0)

    assert type(llm).__name__ == expected_class
