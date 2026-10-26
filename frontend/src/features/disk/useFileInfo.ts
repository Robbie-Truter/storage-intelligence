import { useQuery } from "@tanstack/react-query";
import { queryKeys, toOptionalPath } from "@/lib/api/keys";
import { getFileInfo } from "./api";

/**
 * Hook for GET /api/disk/info.
 * Reports file or directory metadata for `selectedPath`.
 * Enabled only when an entry is selected.
 */
export function useFileInfo(selectedPath?: string | null) {
	const normalizedPath = toOptionalPath(selectedPath);

	return useQuery({
		queryKey: queryKeys.diskInfo(normalizedPath),
		queryFn: () => getFileInfo(normalizedPath),
		enabled: Boolean(normalizedPath),
		staleTime: 60_000,
		gcTime: 300_000,
	});
}
