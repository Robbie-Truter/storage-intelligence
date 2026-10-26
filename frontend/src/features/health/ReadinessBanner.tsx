import { AlertTriangle, CloudOff, ShieldCheck } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { useReadiness } from "./useReadiness";

export function ReadinessBanner() {
	const { state, data } = useReadiness();

	if (state === "loading") {
		return null;
	}

	if (state === "healthy") {
		return (
			<div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
				<Badge variant="outline" className="gap-1.5">
					<ShieldCheck aria-hidden="true" />
					Ready
				</Badge>
				<span>Backend and MCP are available.</span>
			</div>
		);
	}

	if (state === "degraded") {
		return (
			<Alert>
				<AlertTriangle aria-hidden="true" />
				<AlertTitle>MCP unavailable</AlertTitle>
				<AlertDescription>
					<p>
						Storage data and AI analysis are temporarily unavailable while the
						MCP server is offline.
					</p>
					{data?.detail ? <p>{data.detail}</p> : null}
				</AlertDescription>
			</Alert>
		);
	}

	return (
		<Alert variant="destructive">
			<CloudOff aria-hidden="true" />
			<AlertTitle>Backend unreachable</AlertTitle>
			<AlertDescription>
				<p>Cannot reach the backend. Is it running?</p>
				<p>You can keep navigating; data will load when it reconnects.</p>
			</AlertDescription>
		</Alert>
	);
}
