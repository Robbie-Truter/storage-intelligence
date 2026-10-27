import { agentApi } from "@/lib/api/client";
import type {
	AgentAnalyzeRequest,
	AgentAnalyzeResponse,
} from "@/lib/api/types";

export async function analyze(
	request: AgentAnalyzeRequest,
): Promise<AgentAnalyzeResponse> {
	const { data } = await agentApi.post<AgentAnalyzeResponse>(
		"/api/agent/analyze",
		request,
	);
	return data;
}
