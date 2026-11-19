import { Lightbulb } from "lucide-react";
import {
	DIRECTORY_SCAN_LIMIT,
	useDirectoryUsage,
	useFileCounts,
} from "@/features/disk";
import { formatBytes, formatCount, formatPercent } from "@/lib/format";

interface AtAGlanceProps {
	path?: string;
}

export function AtAGlance({ path }: AtAGlanceProps) {
	const { data: directory } = useDirectoryUsage(path, DIRECTORY_SCAN_LIMIT);
	const { data: counts } = useFileCounts(path);

	const entries = directory?.entries ?? [];
	const largest =
		entries.length > 0
			? entries.reduce((max, entry) =>
					entry.size_bytes > max.size_bytes ? entry : max,
				)
			: undefined;
	const listedSize = entries.reduce((sum, entry) => sum + entry.size_bytes, 0);
	const share =
		largest && listedSize > 0
			? (largest.size_bytes / listedSize) * 100
			: undefined;

	const insights: string[] = [];

	if (largest) {
		const shareText =
			share === undefined
				? ""
				: `, ${formatPercent(share)} of the ${entries.length} listed`;
		insights.push(
			`Biggest item shown: ${largest.name} (${formatBytes(largest.size_bytes)}${shareText})`,
		);
	}

	if (counts) {
		insights.push(
			counts.total_files > 0
				? `${formatCount(counts.total_files)} files directly here`
				: "no files directly here",
		);
	}

	if (insights.length === 0) {
		return null;
	}

	return (
		<div className="flex items-start gap-2 rounded-lg border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
			<Lightbulb
				className="mt-0.5 size-4 shrink-0 text-amber-500"
				aria-hidden="true"
			/>
			<p className="leading-relaxed">
				<span className="font-medium text-foreground">At a glance</span>
				{" · "}
				{insights.join(" · ")}
			</p>
		</div>
	);
}
