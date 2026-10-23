"""Model catalog and options for the storage agent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelOption:
    id: str
    label: str
    provider: str
    model_name: str
    mode: str

    @property
    def model_string(self) -> str:
        """The provider-agnostic ``init_chat_model`` string."""
        return f"{self.provider}:{self.model_name}"


MODEL_CATALOG = [
    ModelOption(
        id="openai-gpt-4.1",
        label="GPT-4.1",
        provider="openai",
        model_name="gpt-4.1",
        mode="cloud",
    ),
    ModelOption(
        id="openai-gpt-4.1-mini",
        label="GPT-4.1 Mini",
        provider="openai",
        model_name="gpt-4.1-mini",
        mode="cloud",
    ),
    ModelOption(
        id="google-gemini-3.7-flash",
        label="Gemini 3.7 Flash (Free Tier)",
        provider="google_genai",
        model_name="gemini-3.7-flash",
        mode="cloud",
    ),
    ModelOption(
        id="google-gemini-3.1-flash-lite",
        label="Gemini 3.1 Flash-Lite",
        provider="google_genai",
        model_name="gemini-3.1-flash-lite",
        mode="cloud",
    ),
    ModelOption(
        id="google-gemini-2.5-flash",
        label="Gemini 2.5 Flash",
        provider="google_genai",
        model_name="gemini-2.5-flash",
        mode="cloud",
    ),
    ModelOption(
        id="ollama-llama3.1",
        label="Llama 3.1 (Ollama)",
        provider="ollama",
        model_name="llama3.1",
        mode="local",
    ),
    ModelOption(
        id="ollama-qwen3-8b",
        label="Qwen3 8B (Ollama)",
        provider="ollama",
        model_name="qwen3:8b",
        mode="local",
    ),
]


def find_model(model_id: str) -> ModelOption | None:
    """Return the catalogue entry with ``model_id``, or ``None``."""
    return next((option for option in MODEL_CATALOG if option.id == model_id), None)
