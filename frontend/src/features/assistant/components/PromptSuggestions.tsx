import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Sparkles } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
	PROMPT_SUGGESTIONS,
	type PromptSuggestion,
} from "../data/promptSuggestions";

interface PromptSuggestionsProps {
	disabled?: boolean;
	onSelect: (message: string) => void;
}

export function PromptSuggestions({
	disabled = false,
	onSelect,
}: PromptSuggestionsProps) {
	const [open, setOpen] = useState(false);
	const containerRef = useRef<HTMLDivElement>(null);
	const panelId = useId();

	useEffect(() => {
		if (!open) {
			return;
		}

		const handlePointerDown = (event: PointerEvent) => {
			if (!containerRef.current?.contains(event.target as Node)) {
				setOpen(false);
			}
		};

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				setOpen(false);
			}
		};

		document.addEventListener("pointerdown", handlePointerDown);
		document.addEventListener("keydown", handleKeyDown);
		return () => {
			document.removeEventListener("pointerdown", handlePointerDown);
			document.removeEventListener("keydown", handleKeyDown);
		};
	}, [open]);

	const handleSelect = (suggestion: PromptSuggestion) => {
		setOpen(false);
		onSelect(suggestion.message);
	};

	return (
		<div ref={containerRef}>
			<Button
				type="button"
				variant="outline"
				size="sm"
				className="rounded-full text-muted-foreground hover:text-foreground"
				disabled={disabled}
				aria-expanded={open}
				aria-controls={panelId}
				onClick={() => setOpen((previous) => !previous)}
			>
				<Sparkles className="size-3.5" />
				Prompt ideas
				<ChevronDown
					className={cn(
						"size-3.5 text-muted-foreground transition-transform duration-200",
						open && "rotate-180",
					)}
				/>
			</Button>

			<AnimatePresence initial={false}>
				{open ? (
					<motion.div
						id={panelId}
						role="region"
						aria-label="Predefined prompts"
						initial={{ height: 0, opacity: 0 }}
						animate={{ height: "auto", opacity: 1 }}
						exit={{ height: 0, opacity: 0 }}
						transition={{ duration: 0.25, ease: "easeOut" }}
						className="overflow-hidden"
					>
						<div className="grid gap-2 pt-2 sm:grid-cols-2">
							{PROMPT_SUGGESTIONS.map((suggestion) => (
								<button
									key={suggestion.label}
									type="button"
									className="group flex items-start gap-3 rounded-lg border border-input bg-card p-3 text-left shadow-xs outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
									onClick={() => handleSelect(suggestion)}
								>
									<span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
										<suggestion.icon className="size-4" />
									</span>
									<span className="space-y-1">
										<span className="block text-sm leading-none font-medium">
											{suggestion.label}
										</span>
										<span className="block text-xs leading-snug text-muted-foreground">
											{suggestion.description}
										</span>
									</span>
								</button>
							))}
						</div>
					</motion.div>
				) : null}
			</AnimatePresence>
		</div>
	);
}
