import { AlertCircle, RefreshCw } from "lucide-react";
import { useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectGroup,
	SelectItem,
	SelectLabel,
	SelectSeparator,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { getApiErrorMessage } from "@/lib/api/errors";
import { cn } from "@/lib/utils";
import { useSettings } from "@/providers/SettingsProvider";
import { formatProviderName } from "./format";
import { useModels } from "./useModels";

export function ModelSelector() {
	const { data: models, isPending, isError, error, refetch } = useModels();
	const { modelId, setModelId } = useSettings();

	// Default to the first returned entry without hardcoding IDs
	useEffect(() => {
		if (models && models.length > 0) {
			const currentIsValid = models.some((m) => m.id === modelId);
			if (!modelId || !currentIsValid) {
				setModelId(models[0].id);
			}
		}
	}, [models, modelId, setModelId]);

	// Group models by provider
	const groupedByProvider = useMemo(() => {
		if (!models) return [];
		const groups = new Map<string, typeof models>();
		for (const model of models) {
			const existing = groups.get(model.provider) ?? [];
			existing.push(model);
			groups.set(model.provider, existing);
		}
		return Array.from(groups.entries());
	}, [models]);

	const selectedModel = useMemo(
		() => models?.find((m) => m.id === modelId),
		[models, modelId],
	);

	if (isPending) {
		return (
			<div className="space-y-2">
				<Label htmlFor="model-select">AI Model</Label>
				<Skeleton className="h-9 w-full" />
			</div>
		);
	}

	if (isError) {
		return (
			<div className="space-y-2">
				<Label htmlFor="model-select">AI Model</Label>
				<div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex flex-col sm:flex-row sm:items-center justify-between gap-3">
					<div className="flex items-start gap-2">
						<AlertCircle
							className="size-4 mt-0.5 shrink-0"
							aria-hidden="true"
						/>
						<span>{getApiErrorMessage(error)}</span>
					</div>
					<Button
						type="button"
						variant="outline"
						size="sm"
						onClick={() => refetch()}
						className="shrink-0"
					>
						<RefreshCw className="mr-1.5 size-3.5" aria-hidden="true" />
						Retry
					</Button>
				</div>
			</div>
		);
	}

	if (!models || models.length === 0) {
		return (
			<div className="space-y-2">
				<Label htmlFor="model-select">AI Model</Label>
				<p className="text-sm text-muted-foreground">
					No models available from the backend.
				</p>
			</div>
		);
	}

	return (
		<div className="space-y-2">
			<div className="flex items-center justify-between">
				<Label htmlFor="model-select" className="font-medium text-sm">
					AI Model
				</Label>
				{selectedModel && (
					<span
						className={cn(
							"rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider",
							selectedModel.mode === "local"
								? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
								: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
						)}
					>
						{selectedModel.mode === "local" ? "Local" : "Cloud"}
					</span>
				)}
			</div>

			<Select
				value={modelId ?? undefined}
				onValueChange={(val) => setModelId(val)}
			>
				<SelectTrigger id="model-select" className="w-full">
					<SelectValue placeholder="Select an AI model..." />
				</SelectTrigger>
				<SelectContent className="w-full min-w-[20rem]">
					{groupedByProvider.map(([provider, providerModels], groupIndex) => (
						<SelectGroup key={provider}>
							{groupIndex > 0 && <SelectSeparator />}
							<SelectLabel className="font-semibold text-xs tracking-wider uppercase text-muted-foreground">
								{formatProviderName(provider)}
							</SelectLabel>
							{providerModels.map((model) => (
								<SelectItem key={model.id} value={model.id}>
									<div className="flex items-center justify-between gap-4 w-full">
										<span className="font-medium">{model.label}</span>
										<span className="text-xs text-muted-foreground font-normal">
											{formatProviderName(model.provider)} &bull;{" "}
											{model.mode === "local" ? "Local" : "Cloud"}
										</span>
									</div>
								</SelectItem>
							))}
						</SelectGroup>
					))}
				</SelectContent>
			</Select>

			<p className="text-xs text-muted-foreground">
				{selectedModel?.mode === "local" ? (
					<span className="text-emerald-700 dark:text-emerald-400 font-medium">
						Local model: runs on-device via Ollama without sending data to
						external cloud providers.
					</span>
				) : (
					<span>
						Cloud model: tool results (file paths, names, sizes) are sent to{" "}
						{selectedModel
							? formatProviderName(selectedModel.provider)
							: "the provider"}{" "}
						during analysis.
					</span>
				)}
			</p>
		</div>
	);
}
