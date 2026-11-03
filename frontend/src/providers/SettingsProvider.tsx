import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useMemo,
	useState,
} from "react";
import type { AgentModelOption } from "@/lib/api/types";

interface SettingsContextValue {
	modelId: string | null;
	customModels: AgentModelOption[];
	apiKeys: Record<string, string>;
	setModelId: (modelId: string | null) => void;
	addCustomModel: (provider: string, modelName: string) => void;
	setApiKey: (provider: string, key: string) => void;
	clearApiKey: (provider: string) => void;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

/**
 * Holds the selected model and provider keys in React memory only.
 *
 * Keys are never written to storage, URLs, logs, or error messages.
 */
export function SettingsProvider({ children }: { children: ReactNode }) {
	const [modelId, setModelId] = useState<string | null>(null);
	const [customModels, setCustomModels] = useState<AgentModelOption[]>([]);
	const [apiKeys, setApiKeys] = useState<Record<string, string>>({});

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

	const setApiKey = useCallback((provider: string, key: string) => {
		const trimmedKey = key.trim();
		setApiKeys((current) => {
			if (trimmedKey === "") {
				if (!(provider in current)) {
					return current;
				}
				const next = { ...current };
				delete next[provider];
				return next;
			}
			return { ...current, [provider]: trimmedKey };
		});
	}, []);

	const clearApiKey = useCallback((provider: string) => {
		setApiKeys((current) => {
			if (!(provider in current)) {
				return current;
			}
			const next = { ...current };
			delete next[provider];
			return next;
		});
	}, []);

	const value = useMemo(
		() => ({
			modelId,
			customModels,
			apiKeys,
			setModelId,
			addCustomModel,
			setApiKey,
			clearApiKey,
		}),
		[modelId, customModels, apiKeys, addCustomModel, setApiKey, clearApiKey],
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
