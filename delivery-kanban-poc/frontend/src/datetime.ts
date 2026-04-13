function toDate(value: string): Date | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const direct = new Date(trimmed);
  if (!Number.isNaN(direct.getTime())) {
    return direct;
  }

  const legacy = new Date(trimmed.replace(" ", "T"));
  if (!Number.isNaN(legacy.getTime())) {
    return legacy;
  }

  return null;
}

export function formatDateTimeLocal(value: string): string {
  const parsed = toDate(value);
  if (!parsed) {
    return value;
  }
  return parsed.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function compareDateTimeDesc(left: string, right: string): number {
  const leftDate = toDate(left);
  const rightDate = toDate(right);

  if (leftDate && rightDate) {
    return rightDate.getTime() - leftDate.getTime();
  }
  if (leftDate) {
    return -1;
  }
  if (rightDate) {
    return 1;
  }
  return right.localeCompare(left);
}
