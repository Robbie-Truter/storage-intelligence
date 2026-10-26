import { useState } from "react";
import { PathContextBar } from "@/components/home/PathContextBar";
import { PageHeader } from "@/components/layout/PageHeader";
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
		</div>
	);
}
