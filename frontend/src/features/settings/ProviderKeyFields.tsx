import { Eye, EyeOff, ShieldCheck, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useSettings } from "@/providers/SettingsProvider";
import { formatProviderName } from "./format";
import { useModels } from "./useModels";

export function ProviderKeyFields() {
	const { data: models, isPending, isError } = useModels();
	const { apiKeys, setApiKey, clearApiKey, modelId } = useSettings();
	const [revealedProviders, setRevealedProviders] = useState<
		Record<string, boolean>
	>({});

	// Derive unique providers from fetched models, excluding Ollama
	const cloudProviders = useMemo(() => {
		if (!models) return [];
		const unique = Array.from(new Set(models.map((m) => m.provider)));
		return unique.filter((p) => p.toLowerCase() !== "ollama");
	}, [models]);

	const selectedModel = models?.find((model) => model.id === modelId);
	const selectedProvider = selectedModel?.provider;

	const hasOllama = useMemo(() => {
		if (!models) return false;
		return models.some((m) => m.provider.toLowerCase() === "ollama");
	}, [models]);

	const toggleReveal = (provider: string) => {
		setRevealedProviders((prev) => ({
			...prev,
			[provider]: !prev[provider],
		}));
	};

	if (isPending) {
		return (
			<div className="space-y-4">
				<Skeleton className="h-14 w-full" />
				<Skeleton className="h-14 w-full" />
			</div>
		);
	}

	if (isError || cloudProviders.length === 0) {
		return null;
	}

	return (
		<div className="space-y-5">
			<div className="flex items-center gap-1.5 text-xs text-muted-foreground">
				<ShieldCheck className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
				<span>
					API keys are held in memory only and never saved to disk or storage.
					They are lost on page reload.
				</span>
			</div>

			<div className="space-y-4">
				{cloudProviders.map((provider) => {
					const isRevealed = Boolean(revealedProviders[provider]);
					const currentValue = apiKeys[provider] ?? "";
					const inputId = `api-key-${provider}`;

					return (
						<div key={provider} className="space-y-1.5">
							<div className="flex items-center justify-between">
								<Label htmlFor={inputId} className="text-sm font-medium">
									{formatProviderName(provider)} API Key
								</Label>
								{currentValue !== "" && (
									<span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
										Set in memory
									</span>
								)}
							</div>

							<div className="flex items-center gap-2">
								<div className="relative flex-1">
									<Input
										id={inputId}
										type={isRevealed ? "text" : "password"}
										value={currentValue}
										onChange={(e) => setApiKey(provider, e.target.value)}
										placeholder={`Enter ${formatProviderName(provider)} API key`}
										className="disabled:cursor-not-allowed! pr-10 font-mono text-sm"
										autoComplete="off"
										spellCheck={false}
										disabled={provider !== selectedProvider}
									/>
									<button
										type="button"
										onClick={() => toggleReveal(provider)}
										className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground transition-colors"
										title={isRevealed ? "Hide key" : "Reveal key"}
										disabled={provider !== selectedProvider}
									>
										{isRevealed ? (
											<EyeOff className="size-4" aria-hidden="true" />
										) : (
											<Eye className="size-4" aria-hidden="true" />
										)}
										<span className="sr-only">
											{isRevealed ? "Hide key" : "Reveal key"}
										</span>
									</button>
								</div>

								<Button
									type="button"
									variant="outline"
									size="sm"
									onClick={() => clearApiKey(provider)}
									disabled={currentValue === ""}
									className="shrink-0"
									title="Clear key from memory"
								>
									<X className="mr-1 size-3.5" aria-hidden="true" />
									Clear
								</Button>
							</div>
						</div>
					);
				})}
			</div>

			{hasOllama && (
				<div className="rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
					<p>
						<strong className="text-foreground font-medium">Ollama:</strong>{" "}
						Requires no API key. Models execute on your local machine and data
						does not leave your device.
					</p>
				</div>
			)}
		</div>
	);
}
