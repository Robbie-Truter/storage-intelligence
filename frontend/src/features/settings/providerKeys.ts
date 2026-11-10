import type { CredentialProvider } from "@/lib/api/types";

/**
 * Map a LangChain provider id to the credential-store provider name used by
 * the backend settings API. Returns null for providers without a stored key.
 */
export function credentialProviderFor(
	provider: string,
): CredentialProvider | null {
	const normalized = provider.toLowerCase();
	if (normalized === "openai") {
		return "openai";
	}
	if (normalized === "google" || normalized === "google_genai") {
		return "google";
	}
	return null;
}
