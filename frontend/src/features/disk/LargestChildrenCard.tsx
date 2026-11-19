import { AlertCircle, Folder, FolderOpen, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
	DIRECTORY_SCAN_LIMIT,
	useDirectoryUsage,
} from "@/features/disk/useDirectoryUsage";
import { getApiErrorMessage } from "@/lib/api/errors";
import { formatBytes, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

interface LargestChildrenCardProps {
	path?: string;
	selectedPath?: string;
	onSelectEntry?: (childPath: string) => void;
	onDrillInto?: (childPath: string) => void;
}

const TOP_COUNTS = [5, 10] as const;

function resolveChildPath(parentPath: string, childName: string): string {
	const trimmed = parentPath.trim();
	if (trimmed === "/" || trimmed === "\\") {
		return `${trimmed}${childName}`;
	}
	const sep = trimmed.includes("\\") ? "\\" : "/";
	return `${trimmed.replace(/[/\\]+$/, "")}${sep}${childName}`;
}

export function LargestChildrenCard({
	path,
	selectedPath,
	onSelectEntry,
	onDrillInto,
}: LargestChildrenCardProps) {
	const [topCount, setTopCount] = useState<number>(5);
	const { data, isFetching, isError, error, refetch } = useDirectoryUsage(
		path,
		DIRECTORY_SCAN_LIMIT,
	);

	const allEntries = data?.entries ?? [];
	const directories = allEntries.filter((entry) => entry.type === "directory");
	const entries = directories.slice(0, topCount);
	const scannedTotal = allEntries.reduce(
		(sum, entry) => sum + entry.size_bytes,
		0,
	);

	return (
		<Card className="overflow-hidden">
			<CardHeader>
				<div className="flex items-center justify-between gap-2">
					<CardTitle className="text-base font-semibold">
						Largest directories
					</CardTitle>
					<div className="flex items-center gap-1 rounded-md border p-0.5">
						{TOP_COUNTS.map((count) => (
							<Button
								key={count}
								type="button"
								variant={topCount === count ? "secondary" : "ghost"}
								size="sm"
								onClick={() => setTopCount(count)}
								className="h-6 px-2 text-xs"
								aria-pressed={topCount === count}
							>
								Top {count}
							</Button>
						))}
					</div>
				</div>
				<CardDescription>
					Immediate subdirectories ranked by recursive size. Percentages are
					shares of scanned storage; Open explores a folder deeper.
				</CardDescription>
				{isFetching && (
					<p className="text-xs text-muted-foreground" role="status">
						Scanning folder sizes; this may take a while.
					</p>
				)}
			</CardHeader>
			<CardContent className="space-y-4">
				{isFetching && (
					<div className="space-y-2">
						<Skeleton className="h-10 w-full" />
						<Skeleton className="h-10 w-full" />
						<Skeleton className="h-10 w-full" />
						<Skeleton className="h-10 w-full" />
						<Skeleton className="h-10 w-full" />
					</div>
				)}

				{isError && (
					<div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex flex-col sm:flex-row sm:items-center justify-between gap-3">
						<div className="flex items-start gap-2">
							<AlertCircle
								className="size-4 mt-0.5 shrink-0"
								aria-hidden="true"
							/>
							<span>{getApiErrorMessage(error)}</span>
						</div>
						<Button
							type="button"
							variant="outline"
							size="sm"
							onClick={() => refetch()}
							className="shrink-0"
						>
							<RefreshCw className="mr-1.5 size-3.5" aria-hidden="true" />
							Retry
						</Button>
					</div>
				)}

				{!isFetching && !isError && directories.length === 0 && (
					<p className="text-sm text-muted-foreground py-4 text-center">
						No subdirectories found in this directory.
					</p>
				)}

				{data && entries.length > 0 && (
					<div className="space-y-1.5">
						{entries.map((entry, index) => {
							const childFullPath = resolveChildPath(data.path, entry.name);
							const isSelected = selectedPath === childFullPath;
							const share =
								scannedTotal > 0 ? (entry.size_bytes / scannedTotal) * 100 : 0;
							const barWidth = Math.max(2, Math.round(share));

							return (
								<div
									key={entry.name}
									className={cn(
										"relative group flex w-full items-center justify-between gap-3 rounded-lg border p-2.5 text-left text-sm transition-all overflow-hidden",
										isSelected
											? "border-primary bg-primary/5 ring-1 ring-primary"
											: "border-border/70 bg-card hover:bg-accent/40 hover:border-border",
									)}
								>
									<div
										aria-hidden="true"
										className={cn(
											"absolute inset-y-0 left-0 opacity-15 transition-all pointer-events-none",
											isSelected
												? "bg-primary"
												: "bg-primary/60 group-hover:opacity-25",
										)}
										style={{ width: `${barWidth}%` }}
									/>

									<button
										type="button"
										onClick={() => onSelectEntry?.(childFullPath)}
										className="relative flex min-w-0 flex-1 items-center gap-2.5 text-left z-10 cursor-pointer"
									>
										<span className="font-mono text-xs text-muted-foreground w-4 shrink-0 text-right">
											{index + 1}
										</span>
										<Folder
											className="size-4 shrink-0 text-amber-500"
											aria-hidden="true"
										/>
										<span className="truncate font-medium">{entry.name}</span>
									</button>

									<div className="relative flex shrink-0 items-center gap-2 z-10">
										<div className="text-right">
											<div className="font-mono text-xs font-semibold">
												{formatBytes(entry.size_bytes)}
											</div>
											<div className="text-[10px] text-muted-foreground">
												{formatPercent(share)} of scanned
											</div>
										</div>
										{onDrillInto && (
											<Button
												type="button"
												variant="ghost"
												size="icon"
												onClick={() => onDrillInto(childFullPath)}
												className="size-7 shrink-0 text-muted-foreground hover:text-foreground"
												aria-label={`Open ${entry.name}`}
												title={`Open ${entry.name}`}
											>
												<FolderOpen className="size-4" aria-hidden="true" />
											</Button>
										)}
									</div>
								</div>
							);
						})}
						<p className="text-[11px] text-muted-foreground pt-1">
							Directory sizes cover their entire subtree. Percentages use the
							scanned items returned for this view.
						</p>
					</div>
				)}
			</CardContent>
		</Card>
	);
}
