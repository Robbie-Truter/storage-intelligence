import {
	AlertCircle,
	Calendar,
	Check,
	Clock,
	Copy,
	File,
	Folder,
	Info,
	MousePointerClick,
	RefreshCw,
	X,
} from "lucide-react";
import { useState } from "react";
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
import { useFileInfo } from "@/features/disk/useFileInfo";
import { getApiErrorMessage } from "@/lib/api/errors";
import { formatBytes, formatExtension, formatTimestamp } from "@/lib/format";

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
			// Clipboard API not available or permission denied
		}
	};

	return (
		<Card className="overflow-hidden">
			<CardHeader>
				<div className="flex items-center justify-between gap-2">
					<div className="flex items-center gap-2">
						<Info className="size-5 text-muted-foreground" aria-hidden="true" />
						<CardTitle className="text-base font-semibold">
							Selected entry metadata
						</CardTitle>
					</div>
					{selectedPath && onClearSelection && (
						<Button
							type="button"
							variant="ghost"
							size="sm"
							onClick={onClearSelection}
							className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
						>
							<X className="mr-1 size-3.5" aria-hidden="true" />
							Clear
						</Button>
					)}
				</div>
				<CardDescription>
					Inspection details for the currently selected file or directory.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{!selectedPath && (
					<div className="flex flex-col items-center justify-center gap-2 py-8 text-center text-muted-foreground">
						<MousePointerClick
							className="size-8 opacity-40"
							aria-hidden="true"
						/>
						<p className="text-sm font-medium">No entry selected</p>
						<p className="text-xs max-w-xs">
							Click any item in &ldquo;Largest immediate children&rdquo; above
							to inspect its metadata.
						</p>
					</div>
				)}

				{selectedPath && isPending && (
					<div className="space-y-3">
						<Skeleton className="h-6 w-3/4" />
						<Skeleton className="h-4 w-full" />
						<div className="grid grid-cols-2 gap-3 pt-2">
							<Skeleton className="h-14 w-full" />
							<Skeleton className="h-14 w-full" />
							<Skeleton className="h-14 w-full" />
							<Skeleton className="h-14 w-full" />
						</div>
					</div>
				)}

				{selectedPath && isError && (
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

				{selectedPath && data && (
					<div className="space-y-4">
						{/* Name, Type & Copy path */}
						<div className="space-y-2">
							<div className="flex items-center gap-2 flex-wrap">
								{data.type === "directory" ? (
									<Folder
										className="size-5 shrink-0 text-amber-500"
										aria-hidden="true"
									/>
								) : (
									<File
										className="size-5 shrink-0 text-blue-500"
										aria-hidden="true"
									/>
								)}
								<span className="font-semibold text-base break-all">
									{data.name}
								</span>
								<Badge variant="outline" className="text-xs uppercase">
									{data.type}
								</Badge>
							</div>

							<div className="flex items-center justify-between gap-2 rounded-md border bg-muted/40 px-3 py-1.5 text-xs">
								<span className="font-mono text-muted-foreground truncate">
									{data.path}
								</span>
								<Button
									type="button"
									variant="ghost"
									size="icon"
									onClick={handleCopyPath}
									className="size-6 shrink-0 text-muted-foreground hover:text-foreground"
									title="Copy path"
								>
									{copied ? (
										<Check className="size-3 text-green-500" />
									) : (
										<Copy className="size-3" />
									)}
									<span className="sr-only">Copy path</span>
								</Button>
							</div>
						</div>

						{/* Metadata Grid */}
						<div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
							<div className="rounded-lg border bg-card/60 p-3">
								<p className="text-xs text-muted-foreground font-medium">
									Size
								</p>
								<p className="text-sm font-semibold tracking-tight">
									{formatBytes(data.size_bytes)}
								</p>
							</div>
							<div className="rounded-lg border bg-card/60 p-3">
								<p className="text-xs text-muted-foreground font-medium">
									Extension
								</p>
								<p className="text-sm font-mono font-semibold tracking-tight">
									{formatExtension(data.extension)}
								</p>
							</div>
							<div className="rounded-lg border bg-card/60 p-3 col-span-2 sm:col-span-1">
								<p className="text-xs text-muted-foreground font-medium">
									Entry type
								</p>
								<p className="text-sm font-semibold capitalize tracking-tight">
									{data.type}
								</p>
							</div>
							<div className="rounded-lg border bg-card/60 p-3 col-span-2 sm:col-span-1">
								<div className="flex items-center gap-1 text-muted-foreground">
									<Clock className="size-3" aria-hidden="true" />
									<p className="text-xs font-medium">Modified</p>
								</div>
								<p className="text-xs font-medium tracking-tight mt-0.5">
									{formatTimestamp(data.modified)}
								</p>
							</div>
							<div className="rounded-lg border bg-card/60 p-3 col-span-2 sm:col-span-2">
								<div className="flex items-center gap-1 text-muted-foreground">
									<Calendar className="size-3" aria-hidden="true" />
									<p className="text-xs font-medium">Created</p>
								</div>
								<p className="text-xs font-medium tracking-tight mt-0.5">
									{formatTimestamp(data.created)}
								</p>
							</div>
						</div>

						{/* Directory size notice */}
						{data.type === "directory" && (
							<div className="rounded-md border border-border/80 bg-muted/40 p-2.5 text-xs text-muted-foreground">
								<p className="leading-relaxed">
									<strong className="text-foreground font-medium">Note:</strong>{" "}
									A directory&apos;s{" "}
									<code className="font-mono">size_bytes</code> (
									{formatBytes(data.size_bytes)}) is the filesystem directory
									entry metadata size, not the total size of its contents.
								</p>
							</div>
						)}

						{/* Clear action */}
						{onClearSelection && (
							<div className="pt-1">
								<Button
									type="button"
									variant="outline"
									size="sm"
									onClick={onClearSelection}
								>
									Clear selection
								</Button>
							</div>
						)}
					</div>
				)}
			</CardContent>
		</Card>
	);
}
