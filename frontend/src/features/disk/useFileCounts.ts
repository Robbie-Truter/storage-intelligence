import { useQuery } from "@tanstack/react-query";
import { queryKeys, toOptionalPath } from "@/lib/api/keys";
import { getFileCounts } from "./api";

/**
 * Hook for GET /api/disk/count.
 * Counts files directly inside `path`, grouped by extension.
 * Omits `path` when blank or undefined.
 */
export function useFileCounts(path?: string) {
	const normalizedPath = toOptionalPath(path);

	return useQuery({
		queryKey: queryKeys.diskCount(normalizedPath),
		queryFn: () => getFileCounts(normalizedPath),
		staleTime: 120_000,
		gcTime: 300_000,
	});
}
