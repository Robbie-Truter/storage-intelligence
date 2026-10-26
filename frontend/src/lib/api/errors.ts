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

function getDetailMessage(detail: unknown): string | null {
	if (typeof detail === "string" && detail.trim() !== "") {
		return detail;
	}

	if (Array.isArray(detail)) {
		const messages = detail
			.map((item) =>
				isRecord(item) && typeof item.msg === "string" && item.msg.trim() !== ""
					? item.msg
					: null,
			)
			.filter((message): message is string => message !== null);
		return messages.length > 0 ? messages.join("; ") : "Invalid request";
	}

	if (isRecord(detail) && typeof detail.message === "string") {
		const message = detail.message;
		if (message.trim() === "") {
			return null;
		}
		return typeof detail.tool === "string" && detail.tool.trim() !== ""
			? `${detail.tool}: ${message}`
			: message;
	}

	return null;
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
