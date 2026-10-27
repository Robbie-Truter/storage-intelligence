import { api } from "@/lib/api/client";
import type { AgentModelOption } from "@/lib/api/types";

/**
 * Fetch available model options from the backend.
 * Static catalog; does not require the MCP server or provider keys.
 */
export async function getModels(): Promise<AgentModelOption[]> {
	const { data } = await api.get<AgentModelOption[]>("/api/agent/models");
	return data;
}
