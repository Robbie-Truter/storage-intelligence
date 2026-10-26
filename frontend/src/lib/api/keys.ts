export function toOptionalPath(value: string): string | undefined {
	const trimmed = value.trim();
	return trimmed === "" ? undefined : trimmed;
}

export interface ExploreQueryParams {
	path?: string;
	pattern: string;
	search: string;
	kind: string;
	recursive: boolean;
	maxResults: number;
}

export const queryKeys = {
	readiness: ["health", "ready"] as const,
	diskUsage: (path?: string) => ["disk", "usage", path ?? null] as const,
	diskDirectory: (path: string | undefined, topN: number) =>
		["disk", "directory", path ?? null, topN] as const,
	diskExplore: (params: ExploreQueryParams) =>
		[
			"disk",
			"explore",
			{
				path: params.path ?? null,
				pattern: params.pattern,
				search: params.search,
				kind: params.kind,
				recursive: params.recursive,
				maxResults: params.maxResults,
			},
		] as const,
	diskCount: (path?: string) => ["disk", "count", path ?? null] as const,
	diskInfo: (path?: string) => ["disk", "info", path ?? null] as const,
	agentModels: ["agent", "models"] as const,
};
