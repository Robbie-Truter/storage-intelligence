import { AlertCircle, RefreshCw } from "lucide-react";
import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getApiErrorMessage } from "@/lib/api/errors";
import { formatCount, formatPercent } from "@/lib/format";
import { useFileCounts } from "./useFileCounts";

interface FilesByCategoryCardProps {
	path?: string;
}

type CategoryId = "images" | "videos" | "documents" | "archives" | "appsOther";

interface CategoryCount {
	id: CategoryId;
	label: string;
	count: number;
}

const CATEGORY_ORDER: CategoryId[] = [
	"images",
	"videos",
	"documents",
	"archives",
	"appsOther",
];

const CATEGORY_LABELS: Record<CategoryId, string> = {
	images: "Images",
	videos: "Videos",
	documents: "Documents",
	archives: "Archives",
	appsOther: "Apps & other",
};

const CATEGORY_EXTENSIONS: Record<CategoryId, string[]> = {
	images: [
		".png",
		".jpg",
		".jpeg",
		".gif",
		".webp",
		".svg",
		".bmp",
		".tif",
		".tiff",
		".heic",
		".avif",
		".ico",
	],
	videos: [".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".flv"],
	documents: [
		".pdf",
		".doc",
		".docx",
		".xls",
		".xlsx",
		".ppt",
		".pptx",
		".txt",
		".md",
		".rtf",
		".csv",
		".odt",
		".ods",
		".odp",
		".epub",
	],
	archives: [".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".tgz"],
	appsOther: [],
};

const CATEGORY_LOOKUP = new Map<string, CategoryId>();
for (const id of CATEGORY_ORDER) {
	for (const extension of CATEGORY_EXTENSIONS[id]) {
		CATEGORY_LOOKUP.set(extension, id);
	}
}

function categorize(extension: string): CategoryId {
	const normalized = extension.trim().toLowerCase();
	return CATEGORY_LOOKUP.get(normalized) ?? "appsOther";
}

export function FilesByCategoryCard({ path }: FilesByCategoryCardProps) {
	const { data, isPending, isError, error, refetch } = useFileCounts(path);

	const categories = useMemo<CategoryCount[]>(() => {
		const totals: Record<CategoryId, number> = {
			images: 0,
			videos: 0,
			documents: 0,
			archives: 0,
			appsOther: 0,
		};

		for (const [extension, count] of Object.entries(data?.by_extension ?? {})) {
			totals[categorize(extension)] += count;
		}

		return CATEGORY_ORDER.map((id) => ({
			id,
			label: CATEGORY_LABELS[id],
			count: totals[id],
		})).filter((category) => category.count > 0);
	}, [data]);

	const totalFiles = data?.total_files ?? 0;

	return (
		<Card>
			<CardHeader>
				<CardTitle className="text-base font-semibold">
					Files by category
				</CardTitle>
				<CardDescription>
					Direct files grouped by extension into broad categories. Counts, not
					bytes.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{isPending && (
					<div className="space-y-2">
						<Skeleton className="h-9 w-full" />
						<Skeleton className="h-9 w-full" />
						<Skeleton className="h-9 w-full" />
					</div>
				)}

				{isError && (
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

				{!isPending && !isError && totalFiles === 0 && (
					<p className="py-4 text-center text-sm text-muted-foreground">
						No files found directly in this directory.
					</p>
				)}

				{data && categories.length > 0 && (
					<div className="space-y-2.5">
						{categories.map((category) => {
							const percent =
								totalFiles > 0 ? (category.count / totalFiles) * 100 : 0;
							return (
								<div key={category.id} className="space-y-1">
									<div className="flex items-center justify-between gap-3 text-sm">
										<span className="font-medium">{category.label}</span>
										<span className="font-mono text-xs text-muted-foreground">
											{formatCount(category.count)} · {formatPercent(percent)}
										</span>
									</div>
									<div className="h-2 overflow-hidden rounded-full bg-muted">
										<div
											className="h-full rounded-full bg-primary/70"
											style={{ width: `${Math.max(2, Math.round(percent))}%` }}
										/>
									</div>
								</div>
							);
						})}
						<p className="pt-1 text-[11px] text-muted-foreground">
							Apps & other includes source code, executables, and files with no
							extension.
						</p>
					</div>
				)}
			</CardContent>
		</Card>
	);
}
