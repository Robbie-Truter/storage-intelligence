import { AlertCircle, FileCode, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useFileCounts } from "@/features/disk/useFileCounts";
import { getApiErrorMessage } from "@/lib/api/errors";
import { formatCount, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

interface FilesByExtensionCardProps {
	path?: string;
}

export function FilesByExtensionCard({ path }: FilesByExtensionCardProps) {
	const { data, isPending, isError, error, refetch } = useFileCounts(path);

	const totalFiles = data?.total_files ?? 0;
	const byExtension = data?.by_extension ?? {};

	const sortedEntries = Object.entries(byExtension)
		.map(([ext, count]) => ({
			extension: ext,
			count,
		}))
		.sort((a, b) => b.count - a.count);

	const topEntries = sortedEntries.slice(0, 8);
	const remainderEntries = sortedEntries.slice(8);
	const remainderCount = remainderEntries.reduce((sum, e) => sum + e.count, 0);

	const displayGroups = [
		...topEntries.map((e) => {
			const label =
				e.extension.trim() === "" || e.extension === "(no extension)"
					? "(no extension)"
					: e.extension;
			return {
				label,
				count: e.count,
				isRemainder: false,
			};
		}),
		...(remainderCount > 0
			? [
					{
						label: `Other (${remainderEntries.length} types)`,
						count: remainderCount,
						isRemainder: true,
					},
				]
			: []),
	];

	const maxCount = Math.max(...displayGroups.map((g) => g.count), 1);

	return (
		<Card className="overflow-hidden">
			<CardHeader>
				<div className="flex items-center justify-between gap-2">
					<div className="flex items-center gap-2">
						<FileCode
							className="size-5 text-muted-foreground"
							aria-hidden="true"
						/>
						<CardTitle className="text-base font-semibold">
							Files by extension
						</CardTitle>
					</div>
					{data && (
						<Badge variant="secondary" className="font-mono text-xs">
							{formatCount(totalFiles)} files
						</Badge>
					)}
				</div>
				<CardDescription>
					Distribution of files directly inside this path (non-recursive).
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{isPending && (
					<div className="space-y-2">
						<Skeleton className="h-9 w-full" />
						<Skeleton className="h-9 w-full" />
						<Skeleton className="h-9 w-full" />
						<Skeleton className="h-9 w-full" />
						<Skeleton className="h-9 w-full" />
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

				{!isPending && !isError && totalFiles === 0 && (
					<p className="text-sm text-muted-foreground py-4 text-center">
						No files found directly in this directory.
					</p>
				)}

				{data && totalFiles > 0 && (
					<div className="space-y-1.5">
						{displayGroups.map((group) => {
							const percentageOfTotal = (group.count / totalFiles) * 100;
							const relativeWidth = Math.max(
								2,
								Math.round((group.count / maxCount) * 100),
							);

							return (
								<div
									key={group.label}
									className="relative flex items-center justify-between gap-3 rounded-lg border border-border/70 bg-card p-2.5 text-sm overflow-hidden"
								>
									{/* Relative proportional background bar */}
									<div
										aria-hidden="true"
										className={cn(
											"absolute inset-y-0 left-0 opacity-15 pointer-events-none transition-all",
											group.isRemainder ? "bg-muted-foreground" : "bg-primary",
										)}
										style={{ width: `${relativeWidth}%` }}
									/>

									<div className="relative flex min-w-0 items-center gap-2 z-10">
										<span
											className={cn(
												"font-mono text-xs font-medium truncate",
												group.label === "(no extension)" &&
													"text-muted-foreground italic",
											)}
										>
											{group.label}
										</span>
									</div>

									<div className="relative flex shrink-0 items-center gap-3 z-10 text-xs">
										<span className="font-mono font-medium">
											{formatCount(group.count)}
										</span>
										<span className="text-muted-foreground font-mono w-12 text-right">
											{formatPercent(percentageOfTotal)}
										</span>
									</div>
								</div>
							);
						})}
						<p className="text-[11px] text-muted-foreground pt-1">
							Top extensions shown; remainder grouped. Excludes subfolder
							contents.
						</p>
					</div>
				)}
			</CardContent>
		</Card>
	);
}
