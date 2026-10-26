import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import type { ReadinessResponse } from "@/lib/api/types";
import { getReadiness } from "./api";

export type ReadinessState = "loading" | "healthy" | "degraded" | "offline";

interface UseReadinessResult {
	state: ReadinessState;
	data: ReadinessResponse | undefined;
}

export function useReadiness(): UseReadinessResult {
	const query = useQuery({
		queryKey: queryKeys.readiness,
		queryFn: getReadiness,
		staleTime: 10_000,
		gcTime: 60_000,
		refetchInterval: 30_000,
		retry: 0,
	});

	let state: ReadinessState;
	if (query.isPending) {
		state = "loading";
	} else if (query.isError) {
		state = "offline";
	} else {
		state =
			query.data.status === "ok" && query.data.mcp === "ok"
				? "healthy"
				: "degraded";
	}

	return { state, data: query.data };
}
