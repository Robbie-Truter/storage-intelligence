import { useMemo } from "react";
import { credentialProviderFor } from "@/features/settings/providerKeys";
import { useApiKeyStatus } from "@/features/settings/useApiKeyStatus";
import { useModels } from "@/features/settings/useModels";
import { useSettings } from "@/providers/SettingsProvider";

export function useAnalyzeRequest() {
	const { modelId, customModels } = useSettings();
	const { data: models = [] } = useModels();
	const { data: keyStatus } = useApiKeyStatus();

	const allModels = useMemo(
		() => [...models, ...customModels],
		[models, customModels],
	);

	const selectedModel = useMemo(
		() => allModels.find((model) => model.id === modelId) ?? null,
		[allModels, modelId],
	);

	const hasKey = useMemo(() => {
		if (!selectedModel) {
			return false;
		}
		if (selectedModel.provider.toLowerCase() === "ollama") {
			return true;
		}
		const credential = credentialProviderFor(selectedModel.provider);
		return credential !== null && Boolean(keyStatus?.[credential]);
	}, [keyStatus, selectedModel]);

	return {
		modelId,
		selectedModel,
		hasKey,
	};
}
