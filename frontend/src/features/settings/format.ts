/**
 * Format provider identifier into human-friendly label.
 */
export function formatProviderName(provider: string): string {
	const normalized = provider.toLowerCase();
	if (normalized === "openai") return "OpenAI";
	if (normalized === "google_genai") return "Google GenAI";
	if (normalized === "ollama") return "Ollama";

	return provider
		.split("_")
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join(" ");
}
