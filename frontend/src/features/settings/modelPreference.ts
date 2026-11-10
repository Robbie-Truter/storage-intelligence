interface StoredModel {
	provider: string;
	model_name: string;
}

const MODEL_STORAGE_KEY = "storage-intelligence-model";

/**
 * Read the last selected model. Stored as provider + model name because model
 * ids are not stable across reloads (custom models use random ids).
 */
export function readStoredModel(): StoredModel | null {
	try {
		const raw = localStorage.getItem(MODEL_STORAGE_KEY);
		if (!raw) {
			return null;
		}
		const parsed: unknown = JSON.parse(raw);
		if (typeof parsed !== "object" || parsed === null) {
			return null;
		}
		const { provider, model_name } = parsed as Record<string, unknown>;
		if (typeof provider !== "string" || typeof model_name !== "string") {
			return null;
		}
		return { provider, model_name };
	} catch {
		return null;
	}
}

export function writeStoredModel(model: StoredModel): void {
	try {
		localStorage.setItem(
			MODEL_STORAGE_KEY,
			JSON.stringify({
				provider: model.provider,
				model_name: model.model_name,
			}),
		);
	} catch {
		// Storage can be unavailable (private mode); selection still works in memory.
	}
}
