import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { AgentModelOption } from "@/lib/api/types";

interface ComposerProps {
	path: string;
	question: string;
	onPathChange: (value: string) => void;
	onQuestionChange: (value: string) => void;
	selectedModel: AgentModelOption | null;
	hasKey: boolean;
	canSend: boolean;
	isSending: boolean;
	onSend: () => void;
}

export function Composer({
	path,
	question,
	onPathChange,
	onQuestionChange,
	selectedModel,
	hasKey,
	canSend,
	isSending,
	onSend,
}: ComposerProps) {
	const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
		event.preventDefault();
		if (canSend && !isSending) {
			onSend();
		}
	};

	return (
		<form
			className="space-y-4 rounded-lg border bg-card p-4 shadow-sm"
			onSubmit={handleSubmit}
		>
			<div className="space-y-2">
				<Label htmlFor="assistant-path">Path (optional)</Label>
				<Input
					id="assistant-path"
					placeholder="/Users/you or leave blank for default"
					value={path}
					onChange={(event) => onPathChange(event.target.value)}
				/>
			</div>
			<div className="space-y-2">
				<Label htmlFor="assistant-question">Question (optional)</Label>
				<Textarea
					className="resize-none"
					id="assistant-question"
					placeholder="What should I look for?"
					rows={3}
					value={question}
					onChange={(event) => onQuestionChange(event.target.value)}
					onKeyDown={(event) => {
						if (event.key === "Enter" && !event.shiftKey) {
							event.preventDefault();
							event.currentTarget.form?.requestSubmit();
						}
					}}
				/>
			</div>
			<div className="flex flex-wrap items-center justify-between gap-2">
				<div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
					<span>
						Model:{" "}
						{selectedModel ? (
							<span className="text-foreground">
								{selectedModel.label} ({selectedModel.provider})
							</span>
						) : (
							<span className="text-destructive">None selected</span>
						)}
					</span>
					{selectedModel && selectedModel.provider !== "ollama" ? (
						<Badge variant={hasKey ? "default" : "destructive"}>
							{hasKey ? "Key ready" : "Key missing"}
						</Badge>
					) : selectedModel && selectedModel.provider === "ollama" ? (
						<Badge variant="secondary">Local</Badge>
					) : null}
				</div>
				<Button
					type="submit"
					disabled={!canSend || isSending}
					aria-busy={isSending}
				>
					{isSending ? "Analyzing…" : "Analyze"}
				</Button>
			</div>
			{isSending ? (
				<p className="text-xs text-muted-foreground">
					Analyzing… this can take up to a minute
				</p>
			) : null}
		</form>
	);
}
