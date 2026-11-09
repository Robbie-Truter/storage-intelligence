import { CircleAlert, CircleCheck, LoaderCircle } from "lucide-react";
import {
	Trace,
	TraceCollapsible,
	TraceCollapsibleContent,
	TraceCollapsibleTrigger,
	TraceDescription,
	TraceIcon,
	TraceLine,
	TraceTitle,
} from "@/components/ui/trace";
import type { AgentToolCall } from "@/lib/api/types";
import { summarizeArgs } from "./ToolCallTimeline";

interface ToolTraceProps {
	toolCalls: AgentToolCall[];
	collapsed?: boolean;
}

function toolName(call: AgentToolCall) {
	return call.type.replace("tool-", "");
}

function ToolTraceLine({ call }: { call: AgentToolCall }) {
	const name = toolName(call);
	const args = summarizeArgs(call.input);

	if (call.state === "input-streaming") {
		return (
			<TraceLine status="running">
				<TraceIcon className="mr-1.5 size-3.5">
					<LoaderCircle className="size-3.5 animate-spin" />
				</TraceIcon>
				<TraceTitle>{name}</TraceTitle>
				<TraceDescription className="ml-2">streaming input</TraceDescription>
			</TraceLine>
		);
	}

	if (call.state === "input-available") {
		return (
			<TraceLine status="running">
				<TraceIcon className="mr-1.5 size-3.5">
					<LoaderCircle className="size-3.5 animate-spin" />
				</TraceIcon>
				<TraceTitle>{name}</TraceTitle>
				<TraceDescription className="ml-2">{args}</TraceDescription>
			</TraceLine>
		);
	}

	if (call.state === "output-error") {
		return (
			<TraceLine status="error">
				<TraceIcon className="mr-1.5 size-3.5">
					<CircleAlert className="size-3.5" />
				</TraceIcon>
				<TraceTitle>{name}</TraceTitle>
				<TraceDescription className="ml-2">failed</TraceDescription>
			</TraceLine>
		);
	}

	return (
		<TraceLine>
			<TraceIcon className="mr-1.5 size-3.5">
				<CircleCheck className="size-3.5" />
			</TraceIcon>
			<TraceTitle>{name}</TraceTitle>
			<TraceDescription className="ml-2">{args}</TraceDescription>
		</TraceLine>
	);
}

export function ToolTrace({ toolCalls, collapsed = false }: ToolTraceProps) {
	if (toolCalls.length === 0) {
		return null;
	}

	const lines = toolCalls.map((call) => (
		<ToolTraceLine key={call.toolCallId} call={call} />
	));

	if (!collapsed) {
		return <Trace className="gap-1">{lines}</Trace>;
	}

	return (
		<TraceCollapsible>
			<TraceCollapsibleTrigger className="text-xs">
				<TraceTitle>Tool activity</TraceTitle>
				<TraceDescription className="ml-2">
					{toolCalls.length} {toolCalls.length === 1 ? "call" : "calls"}
				</TraceDescription>
			</TraceCollapsibleTrigger>
			<TraceCollapsibleContent className="text-xs">
				<Trace className="gap-1">{lines}</Trace>
			</TraceCollapsibleContent>
		</TraceCollapsible>
	);
}
