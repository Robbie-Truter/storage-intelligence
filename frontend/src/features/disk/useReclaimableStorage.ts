import { useQuery } from "@tanstack/react-query";
import { queryKeys, toOptionalPath } from "@/lib/api/keys";
import { getReclaimableStorage } from "./api";

interface UseReclaimableStorageOptions {
	enabled?: boolean;
}

/**
 * Hook for GET /api/disk/reclaimable.
 * Disabled by default because the endpoint runs four read-only scans.
 * Omits `path` when blank or undefined.
 */
export function useReclaimableStorage(
	path?: string,
	options: UseReclaimableStorageOptions = {},
) {
	const normalizedPath = toOptionalPath(path);

	return useQuery({
		queryKey: queryKeys.diskReclaimable(normalizedPath),
		queryFn: () => getReclaimableStorage(normalizedPath),
		enabled: options.enabled ?? false,
		staleTime: 300_000,
		gcTime: 600_000,
	});
}
