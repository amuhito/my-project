import { ARCHIVABLE_STATUS, UNHANDLED_STATUS } from "../constants";
import type { CardSummary } from "../types";

type AlertInfo = {
  level: 1 | 2;
  label: string;
};

function todayText() {
  return new Date().toISOString().slice(0, 10);
}

export function canArchiveCard(
  card: Pick<CardSummary, "archived" | "status" | "requested_due_date">,
) {
  if (card.archived) {
    return true;
  }

  return (
    card.status === ARCHIVABLE_STATUS &&
    !!card.requested_due_date &&
    card.requested_due_date < todayText()
  );
}

function countBusinessDaysSince(dateText: string) {
  const baseDate = new Date(`${dateText.slice(0, 10)}T00:00:00`);
  const today = new Date(`${todayText()}T00:00:00`);

  if (Number.isNaN(baseDate.getTime()) || baseDate >= today) {
    return 0;
  }

  let businessDays = 0;
  const current = new Date(baseDate);
  current.setDate(current.getDate() + 1);

  while (current < today) {
    const day = current.getDay();
    if (day !== 0 && day !== 6) {
      businessDays += 1;
    }
    current.setDate(current.getDate() + 1);
  }

  return businessDays;
}

function toAlertLevel(diffDays: number): 0 | 1 | 2 {
  if (diffDays >= 2) {
    return 2;
  }
  if (diffDays >= 1) {
    return 1;
  }
  return 0;
}

export function getAgedAlert(
  card: Pick<CardSummary, "archived" | "status" | "received_date" | "latest_activity_at">,
): AlertInfo | null {
  if (card.archived) {
    return null;
  }

  const activityLevel = card.latest_activity_at
    ? toAlertLevel(countBusinessDaysSince(card.latest_activity_at))
    : 0;
  const receivedLevel =
    card.status === UNHANDLED_STATUS && card.received_date
      ? toAlertLevel(countBusinessDaysSince(card.received_date))
      : 0;

  if (receivedLevel >= activityLevel && receivedLevel > 0) {
    return {
      level: receivedLevel === 2 ? 2 : 1,
      label: receivedLevel >= 2 ? "未対応2営業日以上経過" : "未対応1営業日経過",
    };
  }

  if (activityLevel > 0) {
    return {
      level: activityLevel === 2 ? 2 : 1,
      label: activityLevel >= 2 ? "2営業日以上経過" : "1営業日経過",
    };
  }

  return null;
}
