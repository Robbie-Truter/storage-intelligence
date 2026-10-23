"""Model catalog and options for the storage agent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelOption:
    id: str
    label: str
    provider: str
    model_name: str
    mode: str


MODEL_CATALOG = [
    ModelOption(
        id="openai-gpt",
        label="OpenAI",
        provider="openai",
        model_name="gpt-4.1",
        mode="cloud",
    ),
    ModelOption(
        id="google-gemini",
        label="Google Gemini",
        provider="google_genai",
        model_name="gemini-2.5-flash",
        mode="cloud",
    ),
    ModelOption(
        id="ollama-llama",
        label="Llama 3.1 (Ollama)",
        provider="ollama",
        model_name="llama3.1",
        mode="local",
    ),
]
