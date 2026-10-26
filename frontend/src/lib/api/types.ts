export type DiskEntryType = "file" | "directory";

export interface HealthResponse {
	status: string;
}

export interface ReadinessResponse {
	status: string;
	mcp: string;
	tool_count?: number;
	detail?: string | null;
}

export interface DiskUsageResponse {
	path: string;
	total_bytes: number;
	used_bytes: number;
	free_bytes: number;
	usage_percent: number;
}

export interface DirectoryUsageEntry {
	name: string;
	type: DiskEntryType;
	size_bytes: number;
}

export interface DirectoryDiskUsageResponse {
	path: string;
	entries: DirectoryUsageEntry[];
}

export interface ExploreDirectoryEntry {
	name: string;
	path: string;
	type: string;
}

export interface ExploreDirectoryResponse {
	path: string;
	entries: ExploreDirectoryEntry[];
	truncated: boolean;
}

export interface CountFilesResponse {
	path: string;
	total_files: number;
	by_extension: Record<string, number>;
}

export interface FileInfoResponse {
	name: string;
	path: string;
	type: DiskEntryType;
	size_bytes: number;
	modified: number; // Unix seconds
	created: number; // Unix seconds
	extension: string;
}

export interface AgentModelOption {
	id: string;
	label: string;
	provider: string;
	model_name: string;
	mode: "cloud" | "local" | string;
}

export interface AgentAnalyzeRequest {
	model: string;
	api_key?: string;
	path?: string;
	question?: string;
}

export interface AgentToolCall {
	name: string;
	args: Record<string, unknown>;
	status: "ok" | "error";
	result: unknown;
}

export interface AgentAnalyzeResponse {
	summary: string;
	tool_calls: AgentToolCall[];
}

export interface CleanupExecuteRequest {
	paths: string[];
}

export interface CleanupFailure {
	path: string;
	error: string;
}

export interface CleanupExecuteResponse {
	mode: string;
	paths: string[];
	deleted: string[];
	failed: CleanupFailure[];
	missing_paths: string[];
	total_valid_paths: number;
}
