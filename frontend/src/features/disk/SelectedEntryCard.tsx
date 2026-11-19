import {
	AlertCircle,
	Check,
	Copy,
	File,
	Folder,
	RefreshCw,
	X,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useFileInfo } from "@/features/disk/useFileInfo";
import { getApiErrorMessage } from "@/lib/api/errors";
import { formatBytes, formatTimestamp } from "@/lib/format";

interface SelectedEntryCardProps {
	selectedPath?: string;
	onClearSelection?: () => void;
}

export function SelectedEntryCard({
	selectedPath,
	onClearSelection,
}: SelectedEntryCardProps) {
	const { data, isPending, isError, error, refetch } =
		useFileInfo(selectedPath);
	const [copied, setCopied] = useState(false);

	const handleCopyPath = async () => {
		if (!data?.path) return;
		try {
			await navigator.clipboard.writeText(data.path);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch {
			setCopied(false);
		}
	};

	if (!selectedPath) {
		return null;
	}

	return (
		<Card className="overflow-hidden">
			<CardContent className="space-y-2 py-3">
				{isPending && (
					<div className="space-y-2">
						<Skeleton className="h-5 w-2/3" />
						<Skeleton className="h-8 w-full" />
					</div>
				)}

				{isError && (
					<div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive flex flex-col sm:flex-row sm:items-center justify-between gap-3">
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
					<div className="space-y-2">
						<div className="flex flex-wrap items-center gap-2">
							{data.type === "directory" ? (
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
							<span className="min-w-0 truncate text-sm font-medium">
								{data.name}
							</span>
							<Badge variant="outline" className="text-[10px] uppercase">
								{data.type}
							</Badge>
							<div className="ml-auto flex items-center gap-1">
								<Button
									type="button"
									variant="ghost"
									size="icon"
									onClick={handleCopyPath}
									className="size-6 text-muted-foreground hover:text-foreground"
									title="Copy path"
									aria-label="Copy path"
								>
									{copied ? (
										<Check className="size-3 text-green-500" />
									) : (
										<Copy className="size-3" />
									)}
								</Button>
								{onClearSelection && (
									<Button
										type="button"
										variant="ghost"
										size="icon"
										onClick={onClearSelection}
										className="size-6 text-muted-foreground hover:text-foreground"
										title="Clear selection"
										aria-label="Clear selection"
									>
										<X className="size-3" />
									</Button>
								)}
							</div>
						</div>

						<div className="flex items-center justify-between gap-2 rounded-md border bg-muted/40 px-2.5 py-1.5 text-xs">
							<span
								className="truncate font-mono text-muted-foreground"
								title={data.path}
							>
								{data.path}
							</span>
							<span className="shrink-0 font-semibold">
								{formatBytes(data.size_bytes)}
							</span>
						</div>

						<div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
							<span>Modified {formatTimestamp(data.modified)}</span>
							{data.type === "directory" && (
								<span>Size is the directory entry, not its contents</span>
							)}
						</div>
					</div>
				)}
			</CardContent>
		</Card>
	);
}
