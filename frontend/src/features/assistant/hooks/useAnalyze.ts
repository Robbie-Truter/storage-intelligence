import { useMutation } from "@tanstack/react-query";
import type {
	AgentAnalyzeRequest,
	AgentAnalyzeResponse,
} from "@/lib/api/types";
import { analyze } from "../api/analyze";

export function useAnalyze() {
	return useMutation<AgentAnalyzeResponse, unknown, AgentAnalyzeRequest>({
		mutationFn: analyze,
		retry: 0,
	});
}
