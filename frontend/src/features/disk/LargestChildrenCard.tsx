import { AlertCircle, File, Folder, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDirectoryUsage } from "@/features/disk/useDirectoryUsage";
import { getApiErrorMessage } from "@/lib/api/errors";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

interface LargestChildrenCardProps {
	path?: string;
	selectedPath?: string;
	onSelectEntry?: (childPath: string) => void;
}

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
}: LargestChildrenCardProps) {
	const { data, isPending, isError, error, refetch } = useDirectoryUsage(
		path,
		10,
	);

	const entries = data?.entries ?? [];
	const maxSize = entries.reduce(
		(max, entry) => Math.max(max, entry.size_bytes),
		0,
	);

	return (
		<Card className="overflow-hidden">
			<CardHeader>
				<div className="flex items-center justify-between gap-2">
					<CardTitle className="text-base font-semibold">
						Largest immediate children
					</CardTitle>
					{entries.length > 0 && (
						<span className="text-xs text-muted-foreground">
							Top {entries.length} items
						</span>
					)}
				</div>
				<CardDescription>
					Immediate subdirectories and files ranked by size. Directory sizes are
					recursive totals.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{isPending && (
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

				{!isPending && !isError && entries.length === 0 && (
					<p className="text-sm text-muted-foreground py-4 text-center">
						No entries found in this directory.
					</p>
				)}

				{data && entries.length > 0 && (
					<div className="space-y-1.5">
						{entries.map((entry, index) => {
							const childFullPath = resolveChildPath(data.path, entry.name);
							const isSelected = selectedPath === childFullPath;
							const percentage =
								maxSize > 0
									? Math.max(2, Math.round((entry.size_bytes / maxSize) * 100))
									: 0;

							return (
								<button
									key={entry.name}
									type="button"
									onClick={() => onSelectEntry?.(childFullPath)}
									className={cn(
										"relative group flex w-full items-center justify-between gap-3 rounded-lg border p-2.5 text-left text-sm transition-all overflow-hidden cursor-pointer",
										isSelected
											? "border-primary bg-primary/5 ring-1 ring-primary"
											: "border-border/70 bg-card hover:bg-accent/40 hover:border-border",
									)}
								>
									{/* Proportional background bar visual */}
									<div
										aria-hidden="true"
										className={cn(
											"absolute inset-y-0 left-0 opacity-15 transition-all pointer-events-none",
											isSelected
												? "bg-primary"
												: "bg-primary/60 group-hover:opacity-25",
										)}
										style={{ width: `${percentage}%` }}
									/>

									<div className="relative flex min-w-0 items-center gap-2.5 z-10">
										<span className="font-mono text-xs text-muted-foreground w-4 shrink-0 text-right">
											{index + 1}
										</span>
										{entry.type === "directory" ? (
											<Folder
												className="size-4 shrink-0 text-amber-500"
												aria-hidden="true"
											/>
										) : (
											<File
												className="size-4 shrink-0 text-blue-500"
												aria-hidden="true"
											/>
										)}
										<span className="truncate font-medium">{entry.name}</span>
									</div>

									<div className="relative flex shrink-0 items-center gap-2 z-10">
										<span className="font-mono text-xs font-semibold">
											{formatBytes(entry.size_bytes)}
										</span>
									</div>
								</button>
							);
						})}
						<p className="text-[11px] text-muted-foreground pt-1">
							Note: Directory sizes cover their entire subtree; file sizes cover
							single files. Click a row to select it.
						</p>
					</div>
				)}
			</CardContent>
		</Card>
	);
}
