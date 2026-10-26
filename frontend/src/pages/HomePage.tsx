import { useState } from "react";
import { PathContextBar } from "@/components/home/PathContextBar";
import { PageHeader } from "@/components/layout/PageHeader";
import { LargestChildrenCard, VolumeUsageCard } from "@/features/disk";

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
				<LargestChildrenCard
					path={appliedPath}
					selectedPath={selectedPath}
					onSelectEntry={(path) =>
						setSelectedPath((prev) => (prev === path ? undefined : path))
					}
				/>
			</div>
		</div>
	);
}
