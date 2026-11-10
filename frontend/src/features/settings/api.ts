import { api } from "@/lib/api/client";
import type {
	AgentModelOption,
	ApiKeyStatus,
	ApiKeysUpdateRequest,
} from "@/lib/api/types";

/**
 * Fetch available model options from the backend.
 * Static catalog; does not require the MCP server or provider keys.
 */
export async function getModels(): Promise<AgentModelOption[]> {
	const { data } = await api.get<AgentModelOption[]>("/api/agent/models");
	return data;
}

/**
 * Fetch which providers have a key in the backend's OS credential store.
 * The response only reports presence; actual keys are never returned.
 */
export async function getApiKeyStatus(): Promise<ApiKeyStatus> {
	const { data } = await api.get<ApiKeyStatus>("/api/settings/api-keys");
	return data;
}

/**
 * Store, replace, or clear provider keys in the OS credential store.
 * Omitted providers are left unchanged; an empty string clears that provider.
 */
export async function updateApiKeys(
	payload: ApiKeysUpdateRequest,
): Promise<ApiKeyStatus> {
	const { data } = await api.put<ApiKeyStatus>(
		"/api/settings/api-keys",
		payload,
	);
	return data;
}
