import { Bot, UserRound } from "lucide-react";
import type { AgentToolCall } from "@/lib/api/types";
import { ToolCallTimeline } from "./ToolCallTimeline";

type HistoryItem = {
	role: "user" | "system" | "assistant";
	message: string;
	toolCalls?: AgentToolCall[];
	timestamp: string | Date;
};

function formatTimestamp(ts: string | Date) {
	const date = typeof ts === "string" ? new Date(ts) : ts;
	return date.toLocaleString(undefined, {
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	});
}

export function AssistantConversation({
	role,
	message,
	toolCalls,
	timestamp,
}: HistoryItem) {
	if (!message) {
		return null;
	}

	const timeLabel = formatTimestamp(timestamp);

	return (
		<div className="relative space-y-4 rounded-lg border bg-card p-4 shadow-sm">
			{timeLabel && (
				<span className="absolute right-2 top-2 text-xs text-muted-foreground">
					{timeLabel}
				</span>
			)}
			<div className="space-y-2">
				{role === "user" ? <UserRound /> : <Bot />}

				<p className="whitespace-pre-wrap wrap-break-word text-sm leading-relaxed">
					{message}
				</p>
			</div>

			{role === "assistant" && <ToolCallTimeline toolCalls={toolCalls ?? []} />}
		</div>
	);
}
