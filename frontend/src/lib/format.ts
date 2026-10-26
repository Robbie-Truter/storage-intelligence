const BYTE_UNITS = ["B", "KB", "MB", "GB", "TB"] as const;

const countFormatter = new Intl.NumberFormat();
const timestampFormatter = new Intl.DateTimeFormat(undefined, {
	dateStyle: "medium",
	timeStyle: "medium",
});

export function formatBytes(bytes: number): string {
	if (!Number.isFinite(bytes) || bytes < 0) {
		return "—";
	}

	let scaled = bytes;
	let unitIndex = 0;
	while (scaled >= 1024 && unitIndex < BYTE_UNITS.length - 1) {
		scaled /= 1024;
		unitIndex += 1;
	}

	if (unitIndex === 0) {
		return `${Math.round(scaled)} B`;
	}

	const decimals = scaled >= 100 ? 1 : 2;
	return `${scaled.toFixed(decimals)} ${BYTE_UNITS[unitIndex]}`;
}

export function formatPercent(percent: number): string {
	if (!Number.isFinite(percent)) {
		return "—";
	}
	return `${percent.toFixed(1)}%`;
}

/** Format a Unix-seconds timestamp. */
export function formatTimestamp(seconds: number): string {
	if (!Number.isFinite(seconds)) {
		return "—";
	}
	return timestampFormatter.format(new Date(seconds * 1000));
}

export function formatCount(count: number): string {
	if (!Number.isFinite(count)) {
		return "—";
	}
	return countFormatter.format(count);
}

export function formatExtension(extension: string | null | undefined): string {
	const trimmed = extension?.trim() ?? "";
	return trimmed === "" ? "(none)" : trimmed;
}
