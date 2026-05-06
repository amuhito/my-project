export function pad2(value: number | string) {
  return String(value).padStart(2, "0");
}

export function localDateString(date = new Date()) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

export function monthKey(date: Date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}`;
}

export function normalizeDateInput(raw: string) {
  const value = raw.trim();
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const separated = value.match(/^(\d{1,4})[/-](\d{1,2})(?:[/-](\d{1,2}))?$/);
  if (separated) {
    if (separated[3]) {
      const yyyy = separated[1].length === 4 ? Number(separated[1]) : year;
      return `${yyyy}-${pad2(separated[2])}-${pad2(separated[3])}`;
    }
    return `${year}-${pad2(separated[1])}-${pad2(separated[2])}`;
  }

  if (/^\d{8}$/.test(value)) {
    return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
  }
  if (/^\d{4}$/.test(value)) {
    return `${year}-${value.slice(0, 2)}-${value.slice(2, 4)}`;
  }
  if (/^\d{1,2}$/.test(value)) {
    return `${year}-${pad2(month)}-${pad2(value)}`;
  }
  return value;
}

export function isDatePickerValue(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : "";
}
