import { api } from "@/lib/api/client";
import { toOptionalPath } from "@/lib/api/keys";
import type {
	DirectoryDiskUsageResponse,
	DiskUsageResponse,
} from "@/lib/api/types";

/**
 * Fetch disk usage for the volume containing the given path.
 * When `path` is blank or undefined, the backend defaults to the home directory volume.
 * Omit `path` entirely when blank.
 */
export async function getDiskUsage(path?: string): Promise<DiskUsageResponse> {
	const normalizedPath = toOptionalPath(path);
	const { data } = await api.get<DiskUsageResponse>("/api/disk/usage", {
		params: normalizedPath ? { path: normalizedPath } : undefined,
	});
	return data;
}

/**
 * Rank the immediate children of `path` by size, largest first.
 * When `path` is blank or undefined, the backend defaults to the home directory.
 * Omit `path` entirely when blank.
 */
export async function getDirectoryUsage(
	path?: string,
	topN: number = 10,
): Promise<DirectoryDiskUsageResponse> {
	const normalizedPath = toOptionalPath(path);
	const { data } = await api.get<DirectoryDiskUsageResponse>(
		"/api/disk/directory",
		{
			params: {
				top_n: topN,
				...(normalizedPath ? { path: normalizedPath } : {}),
			},
		},
	);
	return data;
}
