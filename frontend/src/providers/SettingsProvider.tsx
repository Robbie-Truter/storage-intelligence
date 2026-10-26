import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useMemo,
	useState,
} from "react";

interface SettingsContextValue {
	modelId: string | null;
	apiKeys: Record<string, string>;
	setModelId: (modelId: string | null) => void;
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
	const [apiKeys, setApiKeys] = useState<Record<string, string>>({});

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
		() => ({ modelId, apiKeys, setModelId, setApiKey, clearApiKey }),
		[modelId, apiKeys, setApiKey, clearApiKey],
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
