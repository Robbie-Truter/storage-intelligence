import { AnimatePresence, motion } from "framer-motion";
import { MessagesSquare } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useAnalyze } from "@/features/assistant";
import { AssistantConversation } from "@/features/assistant/components/AssistantConversation";
import { Composer } from "@/features/assistant/components/Composer";
import { useAnalyzeRequest } from "@/features/assistant/hooks/useAnalyzeRequest";
import { getApiErrorMessage } from "@/lib/api/errors";
import type { AgentAnalyzeResponse } from "@/lib/api/types";

type HistoryItem = {
	id: string;
	type: "agent" | "user";
	message: AgentAnalyzeResponse | string | null;
	error: string | null;
};

export function AssistantPage() {
	const [path, setPath] = useState("");
	const [question, setQuestion] = useState("");
	const [history, setHistory] = useState<HistoryItem[]>([]);
	const conversationRef = useRef<HTMLDivElement>(null);

	const analyzeMutation = useAnalyze();
	const { modelId, selectedModel, apiKey, hasKey } = useAnalyzeRequest();

	const trimmedPath = path.trim();
	const trimmedQuestion = question.trim();

	const canSend = Boolean(modelId) && !analyzeMutation.isPending;

	// biome-ignore lint/correctness/useExhaustiveDependencies: Only scroll when the message count changes.
	useEffect(() => {
		const el = conversationRef.current;
		if (el) {
			el.scrollTop = el.scrollHeight;
		}
	}, [history.length]);

	const handleSend = () => {
		if (!modelId) {
			return;
		}
		setHistory((current) => [
			...current,
			{
				id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
				type: "user",
				message: trimmedQuestion,
				error: null,
			},
		]);

		setQuestion("");

		const request = {
			model: modelId,
			...(trimmedPath ? { path: trimmedPath } : {}),
			...(trimmedQuestion ? { question: trimmedQuestion } : {}),
			...(apiKey ? { api_key: apiKey } : {}),
		};

		analyzeMutation.mutate(request, {
			onSuccess: (response) => {
				setHistory((current) => [
					...current,
					{
						id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
						type: "agent",
						message: response,
						error: null,
					},
				]);
			},
			onError: (error) => {
				setHistory((current) => [
					...current,
					{
						id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
						type: "agent",
						message: null,
						error: getApiErrorMessage(error),
					},
				]);
			},
		});
	};

	return (
		<div className="flex flex-col justify-evenly gap-3 h-full">
			<PageHeader
				title="AI Assistant"
				description="Ask questions about your storage using read-only tools."
			/>

			<div
				ref={conversationRef}
				aria-live="polite"
				className="h-[50vh] border bg-muted rounded p-4 overflow-y-auto space-y-4"
			>
				<AnimatePresence mode="popLayout">
					{history.length === 0 ? (
						<div className="flex flex-col h-full items-center justify-center gap-2">
							<MessagesSquare size={32} className="text-muted-foreground" />
							<p className="text-sm text-muted-foreground">
								Start a conversation
							</p>
						</div>
					) : (
						history.map((item) => (
							<motion.div
								key={item.id}
								initial={{ opacity: 0, y: 12 }}
								animate={{ opacity: 1, y: 0 }}
								exit={{ opacity: 0, y: -12 }}
								transition={{ duration: 0.2 }}
								className="space-y-2"
							>
								{item.error ? (
									<Alert variant="destructive">
										<AlertDescription>{item.error}</AlertDescription>
									</Alert>
								) : item.message ? (
									<AssistantConversation
										type={item.type}
										message={item.message}
										timestamp={new Date()}
									/>
								) : null}
							</motion.div>
						))
					)}
				</AnimatePresence>

				{analyzeMutation.isPending ? (
					<div className="flex items-center justify-start pl-4">
						<div className="flex items-center gap-1.5 rounded-lg bg-muted px-2 py-2">
							<motion.span
								initial={{ opacity: 0.2, scale: 0.8 }}
								animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1, 0.8] }}
								transition={{ duration: 1.2, repeat: Number.POSITIVE_INFINITY }}
								className="text-lg leading-none text-muted-foreground"
							>
								•
							</motion.span>
							<motion.span
								initial={{ opacity: 0.2, scale: 0.8 }}
								animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1, 0.8] }}
								transition={{
									duration: 1.2,
									repeat: Number.POSITIVE_INFINITY,
									delay: 0.2,
								}}
								className="text-lg leading-none text-muted-foreground"
							>
								•
							</motion.span>
							<motion.span
								initial={{ opacity: 0.2, scale: 0.8 }}
								animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1, 0.8] }}
								transition={{
									duration: 1.2,
									repeat: Number.POSITIVE_INFINITY,
									delay: 0.4,
								}}
								className="text-lg leading-none text-muted-foreground"
							>
								•
							</motion.span>
						</div>
					</div>
				) : null}
			</div>

			<div>
				<Composer
					path={path}
					question={question}
					onPathChange={setPath}
					onQuestionChange={setQuestion}
					selectedModel={selectedModel}
					hasKey={hasKey}
					canSend={canSend}
					isSending={analyzeMutation.isPending}
					onSend={handleSend}
				/>
			</div>
		</div>
	);
}
