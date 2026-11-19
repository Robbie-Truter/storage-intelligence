import {
	AlertCircle,
	Bug,
	Clock,
	Copy,
	FolderMinus,
	RefreshCw,
	ScanSearch,
} from "lucide-react";
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
import { useReclaimableStorage } from "@/features/disk/useReclaimableStorage";
import { getApiErrorMessage } from "@/lib/api/errors";
import type { ReclaimableCategoryId } from "@/lib/api/types";
import { formatBytes, formatCount } from "@/lib/format";

interface ReclaimableStorageCardProps {
	path?: string;
}

function CategoryIcon({ category }: { category: ReclaimableCategoryId }) {
	switch (category) {
		case "duplicates":
			return (
				<Copy className="size-4 shrink-0 text-sky-500" aria-hidden="true" />
			);
		case "junk":
			return (
				<Bug className="size-4 shrink-0 text-rose-500" aria-hidden="true" />
			);
		case "empty_directories":
			return (
				<FolderMinus
					className="size-4 shrink-0 text-amber-500"
					aria-hidden="true"
				/>
			);
		case "other":
			return (
				<Clock className="size-4 shrink-0 text-violet-500" aria-hidden="true" />
			);
		default:
			return (
				<ScanSearch
					className="size-4 shrink-0 text-muted-foreground"
					aria-hidden="true"
				/>
			);
	}
}

export function ReclaimableStorageCard({ path }: ReclaimableStorageCardProps) {
	const [requested, setRequested] = useState(false);
	const { data, isPending, isError, error, refetch } = useReclaimableStorage(
		path,
		{ enabled: requested },
	);

	return (
		<Card>
			<CardHeader>
				<div className="flex items-center justify-between gap-2">
					<CardTitle className="text-base font-semibold">
						Recoverable storage
					</CardTitle>
					{requested && data && (
						<Button
							type="button"
							variant="ghost"
							size="sm"
							onClick={() => refetch()}
							className="h-7 px-2 text-xs"
						>
							<RefreshCw className="mr-1.5 size-3.5" aria-hidden="true" />
							Rescan
						</Button>
					)}
				</div>
				<CardDescription>
					Read-only estimates for duplicate, junk, empty, and stale items. No
					files are changed.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{!requested && (
					<div className="flex flex-col items-start gap-3 rounded-lg border bg-muted/40 p-4">
						<p className="text-sm text-muted-foreground">
							Scan the current path with four read-only tools to estimate
							cleanup candidates.
						</p>
						<Button type="button" size="sm" onClick={() => setRequested(true)}>
							<ScanSearch className="mr-1.5 size-3.5" aria-hidden="true" />
							Scan for cleanup candidates
						</Button>
					</div>
				)}

				{requested && isPending && (
					<div className="space-y-2">
						<Skeleton className="h-16 w-full" />
						<Skeleton className="h-16 w-full" />
						<Skeleton className="h-16 w-full" />
						<Skeleton className="h-16 w-full" />
					</div>
				)}

				{requested && isError && (
					<div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex flex-col sm:flex-row sm:items-center justify-between gap-3">
						<div className="flex items-start gap-2">
							<AlertCircle
								className="mt-0.5 size-4 shrink-0"
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

				{data && (
					<div className="space-y-3">
						<div className="rounded-lg border bg-muted/40 p-4">
							<p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
								Estimated upper bound
							</p>
							<p className="mt-1 text-2xl font-semibold">
								{formatBytes(data.total_estimated_bytes)}
							</p>
							<p className="mt-1 text-[11px] text-muted-foreground">
								Categories may overlap; review before removing anything.
							</p>
						</div>

						<div className="space-y-2">
							{data.categories.map((category) => (
								<div key={category.category} className="rounded-lg border p-3">
									<div className="flex items-start justify-between gap-3">
										<div className="flex min-w-0 items-start gap-2">
											<CategoryIcon category={category.category} />
											<div className="min-w-0">
												<p className="text-sm font-medium">{category.label}</p>
												<p className="text-[11px] text-muted-foreground">
													{formatCount(category.item_count)} items
													{category.group_count > 0 &&
														` · ${formatCount(category.group_count)} groups`}
													{category.truncated && " · sample only"}
												</p>
											</div>
										</div>
										<span className="shrink-0 font-mono text-xs font-semibold">
											{formatBytes(category.estimated_bytes)}
										</span>
									</div>
									<p className="mt-2 text-[11px] text-muted-foreground">
										{category.note}
									</p>
									{category.sample_paths[0] && (
										<p
											className="mt-1 truncate font-mono text-[10px] text-muted-foreground"
											title={category.sample_paths.join("\n")}
										>
											e.g. {category.sample_paths[0]}
										</p>
									)}
								</div>
							))}
						</div>
						<p className="text-[11px] text-muted-foreground">{data.message}</p>
					</div>
				)}
			</CardContent>
		</Card>
	);
}
