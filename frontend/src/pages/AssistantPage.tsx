import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { AnimatePresence, motion } from "framer-motion";
import { MessagesSquare } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AssistantConversation } from "@/features/assistant/components/AssistantConversation";
import { Composer } from "@/features/assistant/components/Composer";
import { ToolTrace } from "@/features/assistant/components/ToolTrace";
import { useAnalyzeRequest } from "@/features/assistant/hooks/useAnalyzeRequest";
import type { AgentToolCall } from "@/lib/api/types";

export function AssistantPage() {
	const [path, setPath] = useState("");
	const [question, setQuestion] = useState("");

	const conversationRef = useRef<HTMLDivElement>(null);

	const { modelId, selectedModel, hasKey } = useAnalyzeRequest();

	const { messages, sendMessage, status, stop, error } = useChat({
		transport: new DefaultChatTransport({
			api: `${import.meta.env.VITE_API_BASE_URL}/api/agent/analyze`,
		}),
	});

	const trimmedPath = path.trim();
	const trimmedQuestion = question.trim();

	const isLoading = status === "submitted" || status === "streaming";
	const canSend = Boolean(modelId) && !isLoading;

	const getMessageText = (message: UIMessage) =>
		message.parts
			.filter((part) => part.type === "text")
			.map((part) => part.text)
			.join("");

	const getMessageToolCalls = (message: UIMessage) =>
		message.parts.filter(
			(part): part is AgentToolCall =>
				part.type.startsWith("tool-") &&
				"state" in part &&
				(part.state === "output-available" || part.state === "output-error"),
		);

	const getTraceToolCalls = (message: UIMessage) =>
		message.parts.filter(
			(part): part is AgentToolCall =>
				part.type.startsWith("tool-") &&
				"state" in part &&
				(part.state === "input-streaming" ||
					part.state === "input-available" ||
					part.state === "output-available" ||
					part.state === "output-error"),
		);

	const messageHistory = messages.map((message) => {
		return {
			id: message.id,
			role: message.role,
			message: getMessageText(message),
			toolCalls: getMessageToolCalls(message),
		};
	});

	const lastMessage = messages.at(-1);

	const lastAssistantMessage =
		lastMessage?.role === "assistant" ? lastMessage : undefined;

	const traceToolCalls = lastAssistantMessage
		? getTraceToolCalls(lastAssistantMessage)
		: [];

	// biome-ignore lint/correctness/useExhaustiveDependencies: Only scroll when the message count changes.
	useLayoutEffect(() => {
		const el = conversationRef.current;
		if (el) {
			el.scrollTop = el.scrollHeight;
		}
	}, [messages]);

	const handleSend = async () => {
		if (!modelId) {
			return;
		}

		let effectiveUserMessage = trimmedQuestion;
		if (!trimmedQuestion) {
			if (trimmedPath) {
				effectiveUserMessage = `Analyze the storage usage under ${trimmedPath} and report what takes the most space.`;
			} else {
				effectiveUserMessage =
					"Analyze the storage usage starting from the default location and report what takes the most space.";
			}
		}

		setQuestion("");

		const request = {
			model: modelId,
			provider: selectedModel?.provider ?? "",
			model_name: selectedModel?.model_name ?? "",
			...(trimmedPath ? { path: trimmedPath } : {}),
			...(trimmedQuestion ? { question: trimmedQuestion } : {}),
		};

		await sendMessage(
			{ text: effectiveUserMessage },
			{
				body: {
					...request,
				},
			},
		);
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
					{messages.length === 0 ? (
						<div className="flex flex-col h-full items-center justify-center gap-2">
							<MessagesSquare size={32} className="text-muted-foreground" />
							<p className="text-sm text-muted-foreground">
								Start a conversation
							</p>
						</div>
					) : (
						messageHistory?.map((message, index) => (
							<motion.div
								key={message.id}
								initial={{ opacity: 0, y: 12 }}
								animate={{ opacity: 1, y: 0 }}
								exit={{ opacity: 0, y: -12 }}
								transition={{ duration: 0.2, delay: 0.2 }}
								className="space-y-2"
							>
								<AssistantConversation
									role={message.role}
									message={message.message}
									toolCalls={message.toolCalls}
									timestamp={new Date()}
								/>

								{error && index === messages.length - 1 && (
									<Alert variant="destructive">
										<AlertDescription>
											<p className="whitespace-pre-wrap wrap-break-word text-sm leading-relaxed">
												Error: {error.message}
											</p>
										</AlertDescription>
									</Alert>
								)}
							</motion.div>
						))
					)}
				</AnimatePresence>

				<AnimatePresence mode="popLayout">
					{isLoading ? (
						<motion.div
							initial={{ opacity: 0, y: 12 }}
							animate={{ opacity: 1, y: 0 }}
							exit={{ opacity: 0, y: -12 }}
							className="flex flex-col items-start gap-1 pl-1"
						>
							<div className="flex items-center gap-1.5 rounded-lg px-2 py-2">
								<motion.span
									animate={{ opacity: [0.4, 1, 0.4] }}
									transition={{
										duration: 1.6,
										repeat: Number.POSITIVE_INFINITY,
									}}
									className="pr-1 text-sm text-muted-foreground"
								>
									Thinking
								</motion.span>
								<motion.span
									initial={{ opacity: 0.2, scale: 0.8 }}
									animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1, 0.8] }}
									transition={{
										duration: 1.2,
										repeat: Number.POSITIVE_INFINITY,
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

							<ToolTrace toolCalls={traceToolCalls} />
						</motion.div>
					) : null}
				</AnimatePresence>

				{!isLoading && traceToolCalls.length > 0 && (
					<motion.div
						initial={{ opacity: 0, y: 12 }}
						animate={{ opacity: 1, y: 0 }}
						className="pl-1"
					>
						<ToolTrace toolCalls={traceToolCalls} collapsed />
					</motion.div>
				)}
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
					isSending={isLoading}
					onSend={handleSend}
					onCancel={stop}
				/>
			</div>
		</div>
	);
}
