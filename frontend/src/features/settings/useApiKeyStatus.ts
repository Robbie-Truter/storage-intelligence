import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import type { ApiKeyStatus } from "@/lib/api/types";
import { getApiKeyStatus } from "./api";

/**
 * Hook for GET /api/settings/api-keys.
 * Reports which providers have a key in the OS credential store; never
 * returns the key itself and never caches anything secret.
 */
export function useApiKeyStatus() {
	return useQuery<ApiKeyStatus>({
		queryKey: queryKeys.apiKeyStatus,
		queryFn: getApiKeyStatus,
		staleTime: 0,
		refetchOnWindowFocus: false,
	});
}
