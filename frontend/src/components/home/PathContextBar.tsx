import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface PathContextBarProps {
	draftValue: string;
	appliedValue: string | undefined;
	onDraftChange: (value: string) => void;
	onApply: () => void;
	onReset: () => void;
}

export function PathContextBar({
	draftValue,
	appliedValue,
	onDraftChange,
	onApply,
	onReset,
}: PathContextBarProps) {
	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") {
			e.preventDefault();
			onApply();
		}
	};

	const confirmationLine =
		appliedValue && appliedValue.trim() !== ""
			? `Applied path: ${appliedValue}`
			: "Using backend default (home)";

	return (
		<div className="space-y-2">
			<div className="flex flex-col gap-2 sm:flex-row sm:items-end">
				<div className="flex-1 space-y-1.5">
					<Label htmlFor="path-context">Path context</Label>
					<Input
						id="path-context"
						type="text"
						value={draftValue}
						onChange={(e) => onDraftChange(e.target.value)}
						onKeyDown={handleKeyDown}
						placeholder="/absolute/path or leave blank for default"
					/>
				</div>
				<div className="flex gap-2">
					<Button type="button" onClick={onApply}>
						Apply
					</Button>
					<Button type="button" variant="outline" onClick={onReset}>
						Reset
					</Button>
				</div>
			</div>
			<p className="text-muted-foreground text-xs">
				Blank means the backend's default (home).
			</p>
			<p className="text-muted-foreground text-xs">{confirmationLine}</p>
		</div>
	);
}
