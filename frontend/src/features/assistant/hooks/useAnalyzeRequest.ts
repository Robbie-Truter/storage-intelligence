import { useMemo } from "react";
import { useModels } from "@/features/settings/useModels";
import { useSettings } from "@/providers/SettingsProvider";

export function useAnalyzeRequest() {
	const { modelId, apiKeys } = useSettings();
	const { data: models = [] } = useModels();

	const selectedModel = useMemo(
		() => models.find((model) => model.id === modelId) ?? null,
		[models, modelId],
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
		apiKey,
		hasKey,
	};
}
