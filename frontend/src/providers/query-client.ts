import { QueryClient } from "@tanstack/react-query";
import axios from "axios";

export const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			refetchOnWindowFocus: false,
			retry: (failureCount, error) => {
				if (failureCount >= 1) {
					return false;
				}

				if (axios.isAxiosError(error)) {
					const status = error.response?.status;
					if (status !== undefined && status >= 400 && status < 500) {
						return false;
					}

					const method = error.config?.method?.toLowerCase();
					if (method !== undefined && method !== "get") {
						return false;
					}
				}

				return true;
			},
		},
		mutations: {
			retry: 0,
		},
	},
});
