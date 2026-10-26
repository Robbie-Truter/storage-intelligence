import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

/** Resolved API origin, shown in Settings. */
export const apiBaseUrl = baseURL;

export const api = axios.create({
	baseURL,
	timeout: 30_000,
	withCredentials: false,
});

export const agentApi = axios.create({
	baseURL,
	timeout: 180_000, // agent runs can take a while; no streaming in v1
	withCredentials: false,
});
