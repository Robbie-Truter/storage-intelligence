import { Bot, UserRound } from "lucide-react";
import type { AgentAnalyzeResponse } from "@/lib/api/types";
import { ToolCallTimeline } from "./ToolCallTimeline";

type HistoryItem = {
	type: "agent" | "user";
	message: AgentAnalyzeResponse | string | null;
};

export function AssistantConversation({ type, message }: HistoryItem) {
	if (!message) {
		return null;
	}

	if (type === "user" && typeof message === "string") {
		return (
			<div className="space-y-4 rounded-lg border bg-card p-4 shadow-sm">
				<div className="space-y-2">
					<UserRound />
					<p className="whitespace-pre-wrap wrap-break-word text-sm leading-relaxed">
						{message}
					</p>
				</div>
			</div>
		);
	}

	if (type === "agent" && typeof message !== "string") {
		return (
			<div className="space-y-4 rounded-lg border bg-card p-4 shadow-sm">
				<div className="space-y-2">
					<Bot />
					<p className="whitespace-pre-wrap wrap-break-word text-sm leading-relaxed">
						{message.summary}
					</p>
				</div>
				<ToolCallTimeline toolCalls={message.tool_calls ?? []} />
			</div>
		);
	}
}
