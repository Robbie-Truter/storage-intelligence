import { ArrowRight, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PathContextBar } from "@/components/home/PathContextBar";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import {
	FilesByExtensionCard,
	LargestChildrenCard,
	SelectedEntryCard,
	VolumeUsageCard,
} from "@/features/disk";

export function HomePage() {
	const [draftPath, setDraftPath] = useState("");
	const [appliedPath, setAppliedPath] = useState<string | undefined>(undefined);
	const [selectedPath, setSelectedPath] = useState<string | undefined>(
		undefined,
	);

	const handleApply = () => {
		const trimmed = draftPath.trim();
		if (trimmed === "") {
			setAppliedPath(undefined);
		} else {
			setAppliedPath(trimmed);
		}
		setSelectedPath(undefined);
	};

	const handleReset = () => {
		setDraftPath("");
		setAppliedPath(undefined);
		setSelectedPath(undefined);
	};

	return (
		<div className="space-y-6">
			<PageHeader
				title="Storage overview"
				description="Inspect volume usage, largest folders, and file counts."
			/>
			<PathContextBar
				draftValue={draftPath}
				appliedValue={appliedPath}
				onDraftChange={setDraftPath}
				onApply={handleApply}
				onReset={handleReset}
			/>
			<div className="grid gap-6">
				<VolumeUsageCard path={appliedPath} />
				<div className="grid gap-6 lg:grid-cols-2">
					<LargestChildrenCard
						path={appliedPath}
						selectedPath={selectedPath}
						onSelectEntry={(path) =>
							setSelectedPath((prev) => (prev === path ? undefined : path))
						}
					/>
					<div className="space-y-6">
						<SelectedEntryCard
							selectedPath={selectedPath}
							onClearSelection={() => setSelectedPath(undefined)}
						/>
						<FilesByExtensionCard path={appliedPath} />
					</div>
				</div>
			</div>

			<div className="relative overflow-hidden rounded-xl border bg-linear-to-r from-card via-card to-accent/20 p-6 shadow-sm">
				<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
					<div className="space-y-1">
						<div className="flex items-center gap-2">
							<Sparkles className="size-5 text-indigo-500" aria-hidden="true" />
							<h3 className="font-semibold text-base tracking-tight">
								Need deeper analysis?
							</h3>
						</div>
						<p className="text-muted-foreground text-sm max-w-xl">
							Ask the AI Assistant to scan for large files, duplicates, stale
							caches, and junk with guided cleanup recommendations.
						</p>
					</div>
					<Button asChild className="shrink-0 group">
						<Link to="/assistant">
							<span>Open AI Assistant</span>
							<ArrowRight
								className="ml-1.5 size-4 transition-transform group-hover:translate-x-0.5"
								aria-hidden="true"
							/>
						</Link>
					</Button>
				</div>
			</div>
		</div>
	);
}
