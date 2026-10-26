import axios from "axios";
import { api } from "@/lib/api/client";
import type { ReadinessResponse } from "@/lib/api/types";

/**
 * Fetch readiness. A 503 is an expected "degraded" payload (MCP unavailable),
 * not an offline backend, so return its body instead of throwing.
 */
export async function getReadiness(): Promise<ReadinessResponse> {
	try {
		const { data } = await api.get<ReadinessResponse>("/health/ready");
		return data;
	} catch (error) {
		if (
			axios.isAxiosError<ReadinessResponse>(error) &&
			error.response?.status === 503
		) {
			return error.response.data;
		}
		throw error;
	}
}
