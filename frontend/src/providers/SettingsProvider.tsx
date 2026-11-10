import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useEffect,
	useMemo,
	useState,
} from "react";
import {
	readStoredModel,
	writeStoredModel,
} from "@/features/settings/modelPreference";
import { useModels } from "@/features/settings/useModels";
import type { AgentModelOption } from "@/lib/api/types";

interface SettingsContextValue {
	modelId: string | null;
	customModels: AgentModelOption[];
	setModelId: (modelId: string | null) => void;
	addCustomModel: (provider: string, modelName: string) => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

/**
 * Holds the selected model and custom models in React state.
 *
 * The selection is restored from localStorage and kept valid against the model
 * catalog, so every route starts with a usable model.
 *
 * Provider API keys are not stored here: the backend's OS credential store is
 * the source of truth, and the settings page manages keys locally.
 */
export function SettingsProvider({ children }: { children: ReactNode }) {
	const [modelId, setModelId] = useState<string | null>(null);
	const [customModels, setCustomModels] = useState<AgentModelOption[]>([]);
	const { data: models } = useModels();

	const allModels = useMemo(
		() => [...(models ?? []), ...customModels],
		[models, customModels],
	);

	const selectedModel = useMemo(
		() => allModels.find((model) => model.id === modelId),
		[allModels, modelId],
	);

	// Restore the last selection by provider + model name, else fall back to the
	// first available entry without hardcoding IDs.
	useEffect(() => {
		if (allModels.length === 0) {
			return;
		}
		if (modelId && allModels.some((model) => model.id === modelId)) {
			return;
		}
		const stored = readStoredModel();
		const restored = stored
			? allModels.find(
					(model) =>
						model.provider === stored.provider &&
						model.model_name === stored.model_name,
				)
			: undefined;
		setModelId(restored?.id ?? allModels[0].id);
	}, [allModels, modelId]);

	// Remember the resolved selection so the next visit starts from it.
	useEffect(() => {
		if (selectedModel) {
			writeStoredModel(selectedModel);
		}
	}, [selectedModel]);

	const addCustomModel = useCallback(
		(provider: string, modelName: string) => {
			const trimmedName = modelName.trim();
			if (!trimmedName) {
				return;
			}

			const existing = customModels.find(
				(model) =>
					model.provider === provider && model.model_name === trimmedName,
			);

			if (existing) {
				setModelId(existing.id);
				return;
			}

			const model: AgentModelOption = {
				id: `custom-${provider}-${crypto.randomUUID()}`,
				label: trimmedName,
				provider,
				model_name: trimmedName,
				mode: provider === "ollama" ? "local" : "cloud",
			};

			setCustomModels((current) => [...current, model]);
			setModelId(model.id);
		},
		[customModels],
	);

	const value = useMemo(
		() => ({
			modelId,
			customModels,
			setModelId,
			addCustomModel,
		}),
		[modelId, customModels, addCustomModel],
	);

	return (
		<SettingsContext.Provider value={value}>
			{children}
		</SettingsContext.Provider>
	);
}

export function useSettings(): SettingsContextValue {
	const context = useContext(SettingsContext);
	if (context === null) {
		throw new Error("useSettings must be used within a SettingsProvider");
	}
	return context;
}
