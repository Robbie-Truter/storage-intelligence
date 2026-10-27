import { Badge } from "@/components/ui/badge";

interface ResultRendererProps {
	toolName: string;
	result: unknown;
}

function isObject(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function renderPreviewTrash(result: unknown) {
	if (!isObject(result)) {
		return null;
	}
	const paths = Array.isArray(result.paths) ? result.paths : [];
	const missing = Array.isArray(result.missing_paths)
		? result.missing_paths
		: [];
	const total =
		typeof result.total_valid_paths === "number"
			? result.total_valid_paths
			: paths.length;
	return (
		<div className="space-y-2">
			<div className="flex flex-wrap items-center gap-2">
				<Badge variant="secondary">Preview</Badge>
				<span className="text-sm text-muted-foreground">
					{total} path{total === 1 ? "" : "s"} ready
				</span>
			</div>
			{typeof result.message === "string" ? (
				<p className="text-sm text-muted-foreground">{result.message}</p>
			) : null}
			{paths.length > 0 ? (
				<div className="space-y-1 rounded-md border p-2">
					{paths.map((path) => (
						<div key={String(path)} className="text-sm break-all">
							{String(path)}
						</div>
					))}
				</div>
			) : null}
			{missing.length > 0 ? (
				<p className="text-xs text-muted-foreground">
					Missing paths: {missing.map((p) => String(p)).join(", ")}
				</p>
			) : null}
		</div>
	);
}

function renderDirectoryUsage(result: unknown) {
	if (!isObject(result)) {
		return null;
	}
	const entries = Array.isArray(result.entries) ? result.entries : [];
	return (
		<div className="space-y-2">
			<p className="text-sm text-muted-foreground">
				{String(result.path ?? "")}
			</p>
			<div className="space-y-1 rounded-md border p-2">
				{entries.map((entry) => {
					if (!isObject(entry)) {
						return null;
					}
					const key = String(entry.name);
					return (
						<div
							key={key}
							className="flex items-center justify-between text-sm"
						>
							<span>
								{String(entry.name)}{" "}
								<span className="text-muted-foreground">
									({String(entry.type)})
								</span>
							</span>
							{typeof entry.size_bytes === "number" ? (
								<span className="text-muted-foreground">
									{entry.size_bytes.toLocaleString()} bytes
								</span>
							) : null}
						</div>
					);
				})}
				{entries.length === 0 ? (
					<p className="text-sm text-muted-foreground">No entries</p>
				) : null}
			</div>
		</div>
	);
}

function renderDiskUsage(result: unknown) {
	if (!isObject(result)) {
		return null;
	}
	return (
		<div className="space-y-1 text-sm">
			<p>Path: {String(result.path ?? "")}</p>
			<p>
				Total:{" "}
				{typeof result.total_bytes === "number"
					? result.total_bytes.toLocaleString()
					: "-"}
			</p>
			<p>
				Used:{" "}
				{typeof result.used_bytes === "number"
					? result.used_bytes.toLocaleString()
					: "-"}
			</p>
			<p>
				Free:{" "}
				{typeof result.free_bytes === "number"
					? result.free_bytes.toLocaleString()
					: "-"}
			</p>
			<p>
				Usage:{" "}
				{typeof result.usage_percent === "number" ? result.usage_percent : "-"}%
			</p>
		</div>
	);
}

function renderExploreDirectory(result: unknown) {
	if (!isObject(result)) {
		return null;
	}
	const entries = Array.isArray(result.entries) ? result.entries : [];
	return (
		<div className="space-y-2">
			<p className="text-sm text-muted-foreground">
				{String(result.path ?? "")}
				{result.truncated ? " (truncated)" : ""}
			</p>
			<div className="space-y-1 rounded-md border p-2">
				{entries.map((entry) => {
					if (!isObject(entry)) {
						return null;
					}
					const key = String(entry.path ?? entry.name);
					return (
						<div key={key} className="text-sm break-all">
							{String(entry.path ?? entry.name)}{" "}
							<span className="text-muted-foreground">
								({String(entry.type)})
							</span>
						</div>
					);
				})}
				{entries.length === 0 ? (
					<p className="text-sm text-muted-foreground">No entries</p>
				) : null}
			</div>
		</div>
	);
}

function renderCountFiles(result: unknown) {
	if (!isObject(result)) {
		return null;
	}
	const byExt = isObject(result.by_extension) ? result.by_extension : {};
	const entries = Object.entries(byExt);
	return (
		<div className="space-y-2">
			<p className="text-sm">
				Total files:{" "}
				{typeof result.total_files === "number" ? result.total_files : "-"}
			</p>
			<div className="space-y-1 rounded-md border p-2">
				{entries.map(([key, value]) => (
					<div key={key} className="flex items-center justify-between text-sm">
						<span>{key === "" ? "(no extension)" : key}</span>
						<span className="text-muted-foreground">{String(value)}</span>
					</div>
				))}
				{entries.length === 0 ? (
					<p className="text-sm text-muted-foreground">No extensions</p>
				) : null}
			</div>
		</div>
	);
}

function renderFileInfo(result: unknown) {
	if (!isObject(result)) {
		return null;
	}
	return (
		<div className="space-y-1 text-sm">
			<p>Name: {String(result.name ?? "")}</p>
			<p>Path: {String(result.path ?? "")}</p>
			<p>Type: {String(result.type ?? "")}</p>
			<p>
				Size:{" "}
				{typeof result.size_bytes === "number"
					? result.size_bytes.toLocaleString()
					: "-"}
			</p>
			<p>
				Modified: {typeof result.modified === "number" ? result.modified : "-"}
			</p>
			<p>
				Created: {typeof result.created === "number" ? result.created : "-"}
			</p>
			<p>
				Extension:{" "}
				{result.extension === "" ? "(none)" : String(result.extension ?? "-")}
			</p>
		</div>
	);
}

function renderArray(result: unknown) {
	if (!Array.isArray(result)) {
		return null;
	}
	if (result.length === 0) {
		return <p className="text-sm text-muted-foreground">Empty result</p>;
	}
	return (
		<div className="space-y-1 rounded-md border p-2">
			{result.slice(0, 20).map((item) => {
				const key =
					typeof item === "string"
						? item
						: isObject(item) && "path" in item
							? String((item as { path?: unknown }).path)
							: JSON.stringify(item);
				return (
					<div key={key} className="text-sm break-all">
						{typeof item === "string" ? item : JSON.stringify(item)}
					</div>
				);
			})}
			{result.length > 20 ? (
				<p className="text-xs text-muted-foreground">
					+{result.length - 20} more
				</p>
			) : null}
		</div>
	);
}

function renderObject(result: unknown) {
	if (!isObject(result)) {
		return null;
	}
	return (
		<pre className="max-h-80 overflow-auto rounded-md border bg-muted/50 p-2 text-xs">
			{JSON.stringify(result, null, 2)}
		</pre>
	);
}

export function ResultRenderer({ toolName, result }: ResultRendererProps) {
	if (toolName === "preview_trash") {
		const rendered = renderPreviewTrash(result);
		if (rendered) {
			return rendered;
		}
	}
	if (toolName === "directory_disk_usage") {
		const rendered = renderDirectoryUsage(result);
		if (rendered) {
			return rendered;
		}
	}
	if (toolName === "disk_usage") {
		const rendered = renderDiskUsage(result);
		if (rendered) {
			return rendered;
		}
	}
	if (toolName === "explore_directory") {
		const rendered = renderExploreDirectory(result);
		if (rendered) {
			return rendered;
		}
	}
	if (toolName === "count_files") {
		const rendered = renderCountFiles(result);
		if (rendered) {
			return rendered;
		}
	}
	if (toolName === "file_info") {
		const rendered = renderFileInfo(result);
		if (rendered) {
			return rendered;
		}
	}
	if (
		toolName === "find_large_files" ||
		toolName === "find_duplicate_files" ||
		toolName === "find_stale_files"
	) {
		const rendered = renderArray(result);
		if (rendered) {
			return rendered;
		}
	}
	if (toolName === "find_empty_directories" || toolName === "find_junk_files") {
		const rendered = renderObject(result);
		if (rendered) {
			return rendered;
		}
	}
	if (Array.isArray(result)) {
		return renderArray(result);
	}
	if (isObject(result)) {
		return renderObject(result);
	}
	if (typeof result === "string") {
		return (
			<p className="text-sm whitespace-pre-wrap wrap-break-word">{result}</p>
		);
	}
	return <p className="text-sm text-muted-foreground">No result</p>;
}
