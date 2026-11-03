import { useMemo } from "react";
import { useModels } from "@/features/settings/useModels";
import { useSettings } from "@/providers/SettingsProvider";

export function useAnalyzeRequest() {
	const { modelId, apiKeys, customModels } = useSettings();
	const { data: models = [] } = useModels();

	const allModels = useMemo(
		() => [...models, ...customModels],
		[models, customModels],
	);

	const selectedModel = useMemo(
		() => allModels.find((model) => model.id === modelId) ?? null,
		[allModels, modelId],
	);

	const isCustomModel = useMemo(
		() => customModels.some((model) => model.id === modelId),
		[customModels, modelId],
	);

	const apiKey = useMemo(() => {
		if (!selectedModel) {
			return undefined;
		}
		if (selectedModel.provider === "ollama") {
			return undefined;
		}
		const key = apiKeys[selectedModel.provider];
		const trimmed = key?.trim();
		return trimmed && trimmed.length > 0 ? trimmed : undefined;
	}, [apiKeys, selectedModel]);

	const hasKey = useMemo(() => {
		if (!selectedModel) {
			return false;
		}
		if (selectedModel.provider === "ollama") {
			return true;
		}
		return apiKey !== undefined;
	}, [apiKey, selectedModel]);

	return {
		modelId,
		selectedModel,
		isCustomModel,
		apiKey,
		hasKey,
	};
}
