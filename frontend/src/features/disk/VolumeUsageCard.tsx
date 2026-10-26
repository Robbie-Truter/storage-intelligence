import { AlertCircle, HardDrive, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useDiskUsage } from "@/features/disk/useDiskUsage";
import { getApiErrorMessage } from "@/lib/api/errors";
import { formatBytes, formatPercent } from "@/lib/format";

interface VolumeUsageCardProps {
	path?: string;
}

export function VolumeUsageCard({ path }: VolumeUsageCardProps) {
	const { data, isPending, isError, error, refetch } = useDiskUsage(path);

	return (
		<Card className="overflow-hidden">
			<CardHeader>
				<div className="flex items-center justify-between gap-2">
					<div className="flex items-center gap-2">
						<HardDrive
							className="size-5 text-muted-foreground"
							aria-hidden="true"
						/>
						<CardTitle className="text-base font-semibold">
							Volume usage
						</CardTitle>
					</div>
					{data && (
						<span className="font-mono text-xs text-muted-foreground truncate max-w-xs sm:max-w-md">
							{data.path}
						</span>
					)}
				</div>
				<CardDescription>
					Reports space for the whole volume containing this path, not only this
					folder.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{isPending && (
					<div className="space-y-4">
						<Skeleton className="h-3 w-full" />
						<div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
							<Skeleton className="h-14 w-full" />
							<Skeleton className="h-14 w-full" />
							<Skeleton className="h-14 w-full" />
							<Skeleton className="h-14 w-full" />
						</div>
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

				{data && (
					<div className="space-y-4">
						<div className="space-y-1.5">
							<div className="flex justify-between text-xs text-muted-foreground font-medium">
								<span>Volume usage</span>
								<span>{formatPercent(data.usage_percent)}</span>
							</div>
							<Progress value={data.usage_percent} className="h-2.5" />
						</div>

						<div className="grid grid-cols-2 gap-3 sm:grid-cols-4 pt-1">
							<div className="rounded-lg border bg-card/60 p-3">
								<p className="text-xs text-muted-foreground font-medium">
									Used
								</p>
								<p className="text-base font-semibold tracking-tight">
									{formatBytes(data.used_bytes)}
								</p>
							</div>
							<div className="rounded-lg border bg-card/60 p-3">
								<p className="text-xs text-muted-foreground font-medium">
									Free
								</p>
								<p className="text-base font-semibold tracking-tight">
									{formatBytes(data.free_bytes)}
								</p>
							</div>
							<div className="rounded-lg border bg-card/60 p-3">
								<p className="text-xs text-muted-foreground font-medium">
									Total
								</p>
								<p className="text-base font-semibold tracking-tight">
									{formatBytes(data.total_bytes)}
								</p>
							</div>
							<div className="rounded-lg border bg-card/60 p-3">
								<p className="text-xs text-muted-foreground font-medium">
									Percent
								</p>
								<p className="text-base font-semibold tracking-tight">
									{formatPercent(data.usage_percent)}
								</p>
							</div>
						</div>
					</div>
				)}
			</CardContent>
		</Card>
	);
}
