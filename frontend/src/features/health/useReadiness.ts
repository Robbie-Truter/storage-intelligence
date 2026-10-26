import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/keys";
import type { ReadinessResponse } from "@/lib/api/types";
import { getReadiness } from "./api";

interface UseReadinessResult {
	isDegraded: boolean;
	isPending: boolean;
	isError: boolean;
	data: ReadinessResponse | undefined;
}

export function useReadiness(): UseReadinessResult {
	const { isPending, isError, data } = useQuery({
		queryKey: queryKeys.readiness,
		queryFn: getReadiness,
		staleTime: 10_000,
		gcTime: 60_000,
		refetchInterval: 30_000,
		retry: 2,
	});

	const isDegraded =
		data !== undefined && (data.status !== "ok" || data.mcp !== "ok");

	return {
		isPending,
		isError,
		isDegraded,
		data,
	};
}
