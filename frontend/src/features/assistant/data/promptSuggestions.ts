import type { LucideIcon } from "lucide-react";
import { Broom, Clock3, Copy, Gauge, HardDrive, Sparkles } from "lucide-react";

export interface PromptSuggestion {
	label: string;
	description: string;
	message: string;
	icon: LucideIcon;
}

export const PROMPT_SUGGESTIONS: readonly PromptSuggestion[] = [
	{
		label: "What's eating my disk?",
		description: "Rank the biggest items and explain what each one is.",
		message:
			"What's taking up the most space in this folder? Rank the biggest items, explain what each one actually is, and note which ones look safe to review later.",
		icon: HardDrive,
	},
	{
		label: "Free space check",
		description: "Total, used, and free space on the volume.",
		message:
			"How much free space is left on my disk, and how full is the volume?",
		icon: Gauge,
	},
	{
		label: "Find duplicates",
		description: "Byte-identical copies and reclaimable space.",
		message:
			"Are there duplicate files in this folder wasting space? Group them, and estimate how much space I could reclaim.",
		icon: Copy,
	},
	{
		label: "Old files",
		description: "Files not modified in over a year, grouped by folder.",
		message:
			"Which files in this folder haven't been modified in over a year? Group them by folder so I can see what's worth reviewing.",
		icon: Clock3,
	},
	{
		label: "Junk inventory",
		description: "Temp files, logs, and build artifacts.",
		message:
			"Show me the junk files and build artifacts (logs, temp files, node_modules, __pycache__, dist, build) in this folder, and how much space they hold.",
		icon: Broom,
	},
	{
		label: "Cleanup plan",
		description: "A ranked, safe-first plan for reclaiming space.",
		message:
			"Review this folder and propose a cleanup plan: junk, duplicates, files untouched for a year, and empty folders. Rank the biggest and safest wins, but don't delete anything.",
		icon: Sparkles,
	},
];
