import { Plus } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { useSettings } from "@/providers/SettingsProvider";
import { formatProviderName } from "./format";

interface CustomModelDialogProps {
	providers: string[];
}

export function CustomModelDialog({ providers }: CustomModelDialogProps) {
	const [open, setOpen] = useState(false);
	const [provider, setProvider] = useState("");
	const [modelName, setModelName] = useState("");
	const { addCustomModel } = useSettings();

	const trimmedName = modelName.trim();
	const canAdd = provider !== "" && trimmedName !== "";

	const handleOpenChange = (nextOpen: boolean) => {
		setOpen(nextOpen);
		if (!nextOpen) {
			setProvider("");
			setModelName("");
		}
	};

	const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
		event.preventDefault();
		if (!canAdd) {
			return;
		}
		addCustomModel(provider, trimmedName);
		handleOpenChange(false);
	};

	return (
		<Dialog open={open} onOpenChange={handleOpenChange}>
			<DialogTrigger asChild>
				<Button
					type="button"
					variant="outline"
					size="icon-sm"
					aria-label="Add custom model"
					title="Add custom model"
				>
					<Plus className="size-4" aria-hidden="true" />
				</Button>
			</DialogTrigger>
			<DialogContent showCloseButton={false}>
				<form onSubmit={handleSubmit} className="space-y-4">
					<DialogHeader>
						<DialogTitle>Add a custom model</DialogTitle>
					</DialogHeader>

					<div className="space-y-2">
						<Label htmlFor="custom-model-provider">Provider</Label>
						<Select value={provider} onValueChange={setProvider}>
							<SelectTrigger id="custom-model-provider" className="w-full">
								<SelectValue placeholder="Select a provider" />
							</SelectTrigger>
							<SelectContent>
								{providers.map((providerId) => (
									<SelectItem key={providerId} value={providerId}>
										{formatProviderName(providerId)}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>

					<div className="space-y-2">
						<Label htmlFor="custom-model-name">Model name</Label>
						<Input
							id="custom-model-name"
							value={modelName}
							onChange={(event) => setModelName(event.target.value)}
							placeholder="e.g. gpt-4.1-mini"
							autoComplete="off"
							spellCheck={false}
						/>
					</div>

					<DialogFooter>
						<Button
							type="button"
							variant="outline"
							onClick={() => handleOpenChange(false)}
						>
							Cancel
						</Button>
						<Button type="submit" disabled={!canAdd}>
							Add model
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}
