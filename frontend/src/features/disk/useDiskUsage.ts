import { useQuery } from "@tanstack/react-query";
import { queryKeys, toOptionalPath } from "@/lib/api/keys";
import { getDiskUsage } from "./api";

/**
 * Hook for GET /api/disk/usage.
 * Reports space for the whole volume containing `path`.
 * Omits `path` when blank or undefined.
 */
export function useDiskUsage(path?: string) {
	const normalizedPath = toOptionalPath(path);

	return useQuery({
		queryKey: queryKeys.diskUsage(normalizedPath),
		queryFn: () => getDiskUsage(normalizedPath),
		staleTime: 60_000,
		gcTime: 300_000,
	});
}
