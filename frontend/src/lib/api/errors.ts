import axios from "axios";

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null;
}

function getDetail(data: unknown): unknown {
	if (isRecord(data) && "detail" in data) {
		return data.detail;
	}
	return null;
}

function extractFromObject(obj: unknown): string | null {
	if (typeof obj === "string" && obj.trim() !== "") {
		return obj.trim();
	}

	if (Array.isArray(obj)) {
		const messages = obj
			.map((item) =>
				isRecord(item) && typeof item.msg === "string" && item.msg.trim() !== ""
					? item.msg
					: typeof item === "string" && item.trim() !== ""
						? item.trim()
						: null,
			)
			.filter((message): message is string => message !== null);
		return messages.length > 0 ? messages.join("; ") : "Invalid request";
	}

	if (isRecord(obj)) {
		if (typeof obj.message === "string" && obj.message.trim() !== "") {
			const message = obj.message.trim();
			return typeof obj.tool === "string" && obj.tool.trim() !== ""
				? `${obj.tool}: ${message}`
				: message;
		}

		if (typeof obj.detail === "string" && obj.detail.trim() !== "") {
			return formatErrorMessage(obj.detail);
		}

		if (Array.isArray(obj.detail)) {
			return extractFromObject(obj.detail);
		}

		if (isRecord(obj.detail)) {
			return extractFromObject(obj.detail);
		}

		if (typeof obj.error === "string" && obj.error.trim() !== "") {
			return obj.error.trim();
		}

		if (isRecord(obj.error)) {
			return extractFromObject(obj.error);
		}
	}

	return null;
}

/**
 * Format a raw error string, safely parsing embedded or direct JSON into human-readable text.
 */
export function formatErrorMessage(error: unknown): string {
	if (typeof error !== "string") {
		return "Something went wrong.";
	}

	const trimmed = error.trim();
	if (!trimmed) {
		return "Something went wrong.";
	}

	// 1. Direct JSON check
	if (
		(trimmed.startsWith("{") && trimmed.endsWith("}")) ||
		(trimmed.startsWith("[") && trimmed.endsWith("]"))
	) {
		try {
			const parsed = JSON.parse(trimmed);
			const extracted = extractFromObject(parsed);
			if (extracted) {
				return extracted;
			}
		} catch {
			// Might be a Python dict with single quotes, e.g. {'message': '...'}
			try {
				const jsonified = trimmed.replace(/'/g, '"');
				const parsed = JSON.parse(jsonified);
				const extracted = extractFromObject(parsed);
				if (extracted) {
					return extracted;
				}
			} catch {
				// Not JSON
			}
		}
	}

	// 2. Embedded JSON block check: e.g. "Prefix: { ... }"
	const jsonStart = trimmed.indexOf("{");
	const jsonEnd = trimmed.lastIndexOf("}");
	if (jsonStart !== -1 && jsonEnd > jsonStart) {
		const prefix = trimmed.slice(0, jsonStart).trim().replace(/:\s*$/, "");
		const candidate = trimmed.slice(jsonStart, jsonEnd + 1);
		try {
			const parsed = JSON.parse(candidate);
			const extracted = extractFromObject(parsed);
			if (extracted) {
				return prefix ? `${prefix}: ${extracted}` : extracted;
			}
		} catch {
			// Ignore JSON parse failure
		}
	}

	return trimmed;
}

function getDetailMessage(detail: unknown): string | null {
	if (typeof detail === "string" && detail.trim() !== "") {
		return formatErrorMessage(detail);
	}

	return extractFromObject(detail);
}

/**
 * Normalize an API failure into a message safe to show to the user.
 *
 * Never reads or interpolates the Axios config, request body, headers, or URL,
 * so provider keys and secret-bearing queries cannot leak into the UI.
 */
export function getApiErrorMessage(error: unknown): string {
	if (!axios.isAxiosError(error)) {
		return "Something went wrong.";
	}

	if (error.response) {
		const detailMessage = getDetailMessage(getDetail(error.response.data));
		if (detailMessage !== null) {
			return detailMessage;
		}
		return `Request failed (HTTP ${error.response.status})`;
	}

	if (error.code === "ECONNABORTED") {
		return "The request timed out.";
	}

	return "Cannot reach the backend. Is it running?";
}
