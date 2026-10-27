import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import type { AgentModelOption } from "@/lib/api/types";
import { getModels } from "./api";

/**
 * Hook for GET /api/agent/models.
 * Cached indefinitely in memory; gcTime 1 hour. No polling.
 */
export function useModels() {
	return useQuery<AgentModelOption[]>({
		queryKey: queryKeys.agentModels,
		queryFn: getModels,
		staleTime: Number.POSITIVE_INFINITY,
		gcTime: 60 * 60 * 1000, // 1 hour
		refetchOnWindowFocus: false,
		refetchInterval: false,
	});
}
