import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import type { AgentToolCall } from "@/lib/api/types";
import { ResultRenderer } from "./ResultRenderer";

interface ToolCallTimelineProps {
	toolCalls: AgentToolCall[];
}

function summarizeArgs(args: Record<string, unknown>): string {
	try {
		const entries = Object.entries(args);
		if (entries.length === 0) {
			return "No arguments";
		}
		const parts = entries.slice(0, 3).map(([key, value]) => {
			if (value === null || value === undefined) {
				return `${key}: -`;
			}
			if (typeof value === "string") {
				return `${key}: ${value.length > 40 ? `${value.slice(0, 37)}...` : value}`;
			}
			return `${key}: ${String(value)}`;
		});
		if (entries.length > 3) {
			parts.push(`+${entries.length - 3} more`);
		}
		return parts.join(", ");
	} catch {
		return "Args";
	}
}

export function ToolCallTimeline({ toolCalls }: ToolCallTimelineProps) {
	if (toolCalls.length === 0) {
		return null;
	}
	return (
		<div className="space-y-2">
			<h3 className="text-sm font-medium">Tool calls</h3>
			<Accordion type="multiple" className="w-full">
				{toolCalls.map((call, index) => {
					const value = `${call.name}-${index}`;
					return (
						<AccordionItem key={value} value={value}>
							<AccordionTrigger className="text-left">
								<div className="flex flex-1 items-center justify-between gap-2 pr-2">
									<div className="flex flex-col">
										<span className="font-medium">{call.name}</span>
										<span className="text-xs text-muted-foreground">
											{summarizeArgs(call.args ?? {})}
										</span>
									</div>
									<Badge
										variant={call.status === "ok" ? "default" : "destructive"}
									>
										{call.status === "ok" ? "ok" : "error"}
									</Badge>
								</div>
							</AccordionTrigger>
							<AccordionContent>
								{call.status === "error" ? (
									<div className="space-y-2">
										<p className="text-sm text-destructive">
											{typeof call.result === "string"
												? call.result
												: "Tool returned an error."}
										</p>
									</div>
								) : (
									<ResultRenderer toolName={call.name} result={call.result} />
								)}
							</AccordionContent>
						</AccordionItem>
					);
				})}
			</Accordion>
		</div>
	);
}
