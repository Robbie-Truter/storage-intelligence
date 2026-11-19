import { useQuery } from "@tanstack/react-query";
import { queryKeys, toOptionalPath } from "@/lib/api/keys";
import { getDirectoryUsage } from "./api";

export const DIRECTORY_SCAN_LIMIT = 50;

/**
 * Hook for GET /api/disk/directory.
 * Ranks immediate children of `path` by size, largest first.
 * Omit `path` when blank or undefined.
 */
export function useDirectoryUsage(path?: string, topN: number = 10) {
	const normalizedPath = toOptionalPath(path);

	return useQuery({
		queryKey: queryKeys.diskDirectory(normalizedPath, topN),
		queryFn: () => getDirectoryUsage(normalizedPath, topN),
		staleTime: 300_000,
		gcTime: 600_000,
	});
}
