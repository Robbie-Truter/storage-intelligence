import { ArrowRight, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { AtAGlance } from "@/components/home/AtAGlance";
import { PathContextBar } from "@/components/home/PathContextBar";
import { ReclaimableStorageCard } from "@/components/home/ReclaimableStorageCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { PROMPT_SUGGESTIONS } from "@/features/assistant/data/promptSuggestions";
import type { AssistantPrefill } from "@/features/assistant/types";
import {
	FilesByCategoryCard,
	FilesByExtensionCard,
	LargestChildrenCard,
	SelectedEntryCard,
	useDiskUsage,
	VolumeUsageCard,
} from "@/features/disk";

const HOME_PROMPT_LABELS = new Set([
	"What's eating my disk?",
	"Find duplicates",
	"Old files",
	"Junk inventory",
	"Cleanup plan",
]);

const HOME_PROMPTS = PROMPT_SUGGESTIONS.filter((suggestion) =>
	HOME_PROMPT_LABELS.has(suggestion.label),
);

export function HomePage() {
	const [draftPath, setDraftPath] = useState("");
	const [appliedPath, setAppliedPath] = useState<string | undefined>(undefined);
	const [selectedPath, setSelectedPath] = useState<string | undefined>(
		undefined,
	);

	const { data: usage } = useDiskUsage(appliedPath);

	const handleApply = () => {
		const trimmed = draftPath.trim();
		setAppliedPath(trimmed === "" ? undefined : trimmed);
		setSelectedPath(undefined);
	};

	const handleReset = () => {
		setDraftPath("");
		setAppliedPath(undefined);
		setSelectedPath(undefined);
	};

	const handleDrillInto = (childPath: string) => {
		setDraftPath(childPath);
		setAppliedPath(childPath);
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
				resolvedPath={usage?.path}
				onDraftChange={setDraftPath}
				onApply={handleApply}
				onReset={handleReset}
			/>
			<AtAGlance path={appliedPath} />
			<div className="grid gap-6">
				<VolumeUsageCard path={appliedPath} />
				<div className="grid gap-6 lg:grid-cols-2">
					<LargestChildrenCard
						path={appliedPath}
						selectedPath={selectedPath}
						onSelectEntry={(path) =>
							setSelectedPath((prev) => (prev === path ? undefined : path))
						}
						onDrillInto={handleDrillInto}
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

			<div className="grid gap-6 lg:grid-cols-2">
				<ReclaimableStorageCard path={appliedPath} />
				<FilesByCategoryCard path={appliedPath} />
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
						<div className="flex flex-wrap gap-2 pt-1">
							{HOME_PROMPTS.map((suggestion) => (
								<Button
									key={suggestion.label}
									asChild
									variant="outline"
									size="sm"
									className="rounded-full"
								>
									<Link
										to="/assistant"
										state={
											{
												path: appliedPath,
												question: suggestion.message,
											} satisfies AssistantPrefill
										}
									>
										<suggestion.icon className="size-3.5" aria-hidden="true" />
										{suggestion.label}
									</Link>
								</Button>
							))}
						</div>
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
