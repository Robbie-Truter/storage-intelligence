import { useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, ShieldCheck, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { getApiErrorMessage } from "@/lib/api/errors";
import { queryKeys } from "@/lib/api/keys";
import type {
	ApiKeyStatus,
	ApiKeysUpdateRequest,
	CredentialProvider,
} from "@/lib/api/types";
import { useSettings } from "@/providers/SettingsProvider";
import { updateApiKeys } from "./api";
import { formatProviderName } from "./format";
import { credentialProviderFor } from "./providerKeys";
import { useApiKeyStatus } from "./useApiKeyStatus";
import { useModels } from "./useModels";

interface KeyDraft {
	value: string;
	touched: boolean;
	clearRequested: boolean;
}

type Feedback = { tone: "success" | "error"; message: string } | null;

const EMPTY_DRAFT: KeyDraft = {
	value: "",
	touched: false,
	clearRequested: false,
};

const MASKED_KEY = "••••••••••••••••";

export function ProviderKeyFields() {
	const { data: models, isPending, isError } = useModels();
	const { customModels } = useSettings();
	const queryClient = useQueryClient();
	const {
		data: keyStatus,
		isPending: isKeyStatusPending,
		isError: isKeyStatusError,
		refetch: refetchKeyStatus,
	} = useApiKeyStatus();

	const [configured, setConfigured] = useState<ApiKeyStatus>({
		openai: false,
		google: false,
	});
	const [drafts, setDrafts] = useState<Record<string, KeyDraft>>({});
	const [revealedProviders, setRevealedProviders] = useState<
		Record<string, boolean>
	>({});
	const [feedback, setFeedback] = useState<Feedback>(null);
	const [isSaving, setIsSaving] = useState(false);

	useEffect(() => {
		if (keyStatus) {
			setConfigured(keyStatus);
		}
	}, [keyStatus]);

	// Derive unique cloud providers from fetched models, mapped to the
	// credential-store provider names the settings API understands.
	const cloudProviders = useMemo(() => {
		if (!models) {
			return [];
		}
		const fields: { provider: string; credential: CredentialProvider }[] = [];
		const seen = new Set<CredentialProvider>();
		for (const model of models) {
			const credential = credentialProviderFor(model.provider);
			if (!credential || seen.has(credential)) {
				continue;
			}
			seen.add(credential);
			fields.push({ provider: model.provider, credential });
		}
		return fields;
	}, [models]);

	const allModels = useMemo(
		() => [...(models ?? []), ...customModels],
		[models, customModels],
	);

	const hasOllama = useMemo(
		() => allModels.some((m) => m.provider.toLowerCase() === "ollama"),
		[allModels],
	);

	const draftFor = (credential: CredentialProvider): KeyDraft =>
		drafts[credential] ?? EMPTY_DRAFT;

	const setDraft = (credential: CredentialProvider, draft: KeyDraft) => {
		setDrafts((current) => ({ ...current, [credential]: draft }));
	};

	const handleValueChange = (credential: CredentialProvider, value: string) => {
		setFeedback(null);
		setDraft(credential, { value, touched: true, clearRequested: false });
	};

	const handleClear = (credential: CredentialProvider) => {
		setFeedback(null);
		setDraft(credential, { value: "", touched: true, clearRequested: true });
	};

	const toggleReveal = (provider: string) => {
		setRevealedProviders((prev) => ({
			...prev,
			[provider]: !prev[provider],
		}));
	};

	const hasPendingChanges = useMemo(
		() =>
			cloudProviders.some(({ credential }) => {
				const draft = drafts[credential];
				if (!draft?.touched) {
					return false;
				}
				if (draft.clearRequested) {
					return configured[credential] || draft.value !== "";
				}
				if (draft.value.trim() !== "") {
					return true;
				}
				return configured[credential];
			}),
		[cloudProviders, drafts, configured],
	);

	const handleSave = async () => {
		if (isSaving) {
			return;
		}

		const payload: ApiKeysUpdateRequest = {};
		for (const { credential } of cloudProviders) {
			const draft = drafts[credential];
			if (!draft?.touched) {
				continue;
			}
			if (draft.clearRequested) {
				if (configured[credential]) {
					payload[credential] = "";
				}
				continue;
			}
			const trimmed = draft.value.trim();
			if (trimmed !== "") {
				payload[credential] = trimmed;
			} else if (configured[credential]) {
				payload[credential] = "";
			}
		}

		if (Object.keys(payload).length === 0) {
			return;
		}

		setFeedback(null);
		setIsSaving(true);
		try {
			const status = await updateApiKeys(payload);
			setConfigured(status);
			queryClient.setQueryData(queryKeys.apiKeyStatus, status);
			setDrafts({});
			setRevealedProviders({});
			setFeedback({
				tone: "success",
				message: "API keys saved to the OS credential store.",
			});
		} catch (error) {
			setFeedback({ tone: "error", message: getApiErrorMessage(error) });
		} finally {
			setIsSaving(false);
		}
	};

	if (isPending || isKeyStatusPending) {
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
			<div className="flex items-start gap-1.5 text-xs text-muted-foreground">
				<ShieldCheck className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
				<span>
					API keys are stored securely in your operating system's credential
					store, never in this app's database or files. Only whether a key is
					saved is shown here.
				</span>
			</div>

			{isKeyStatusError ? (
				<div className="flex items-center justify-between gap-3 rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
					<span>Could not load saved key status.</span>
					<Button
						type="button"
						variant="outline"
						size="sm"
						onClick={() => void refetchKeyStatus()}
					>
						Retry
					</Button>
				</div>
			) : null}

			<div className="space-y-4">
				{cloudProviders.map(({ provider, credential }) => {
					const draft = draftFor(credential);
					const isRevealed = Boolean(revealedProviders[provider]);
					const isConfigured = configured[credential];
					const showSavedPlaceholder =
						isConfigured && !draft.touched && !draft.clearRequested;
					const willClear = draft.clearRequested && isConfigured;
					const inputId = `api-key-${provider}`;
					const isDisabled = isSaving;
					const placeholder = showSavedPlaceholder
						? MASKED_KEY
						: `Enter ${formatProviderName(provider)} API key`;

					return (
						<div key={provider} className="space-y-1.5">
							<div className="flex items-center justify-between">
								<Label htmlFor={inputId} className="text-sm font-medium">
									{formatProviderName(provider)} API Key
								</Label>
								{willClear ? (
									<span className="text-[11px] font-medium text-amber-600 dark:text-amber-400">
										Will be removed on save
									</span>
								) : isConfigured ? (
									<span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
										Saved in credential store
									</span>
								) : null}
							</div>

							<div className="flex items-center gap-2">
								<div className="relative flex-1">
									<Input
										id={inputId}
										type={isRevealed ? "text" : "password"}
										value={draft.value}
										onChange={(e) =>
											handleValueChange(credential, e.target.value)
										}
										placeholder={placeholder}
										className="disabled:cursor-not-allowed! pr-10 font-mono text-sm"
										autoComplete="off"
										spellCheck={false}
										disabled={isDisabled}
									/>
									<button
										type="button"
										onClick={() => toggleReveal(provider)}
										className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground transition-colors"
										title={isRevealed ? "Hide key" : "Reveal key"}
										disabled={isDisabled}
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
									onClick={() => handleClear(credential)}
									disabled={
										(!isConfigured && draft.value === "") ||
										draft.clearRequested ||
										isSaving
									}
									className="shrink-0"
									title="Remove key from credential store"
								>
									<X className="mr-1 size-3.5" aria-hidden="true" />
									Clear
								</Button>
							</div>
						</div>
					);
				})}
			</div>

			<div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
				<div className="text-xs" aria-live="polite">
					{feedback ? (
						<span
							className={
								feedback.tone === "error"
									? "text-destructive"
									: "text-emerald-600 dark:text-emerald-400"
							}
						>
							{feedback.message}
						</span>
					) : (
						<span className="text-muted-foreground">
							{hasPendingChanges ? "Unsaved changes." : "No pending changes."}
						</span>
					)}
				</div>
				<Button
					type="button"
					onClick={handleSave}
					disabled={!hasPendingChanges || isSaving}
					aria-busy={isSaving}
				>
					{isSaving ? "Saving…" : "Save API Keys"}
				</Button>
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
