import { useState } from "react";
import type { Card } from "../types";
import { isRework } from "../utils/card";
import { addDays, localDateString, mondayOfWeek, monthKey, pad2 } from "../utils/date";

export function CalendarView({ cards, onOpen }: { cards: Card[]; onOpen: (id: number) => void }) {
  const [displayMonth, setDisplayMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });
  const [displayWeek, setDisplayWeek] = useState(() => mondayOfWeek(new Date()));
  const [mode, setMode] = useState<"month" | "week">("month");
  const todayKey = localDateString();
  const currentMonthKey = monthKey(displayMonth);
  const weekdays = mode === "month" ? ["日", "月", "火", "水", "木", "金", "土"] : ["月", "火", "水", "木", "金", "土", "日"];
  const entriesByDay = new Map<string, { card: Card; kind: "予定" | "納期" }[]>();
  const weekDays = Array.from({ length: 7 }, (_, index) => localDateString(addDays(displayWeek, index)));
  const visibleDaySet = new Set(mode === "month" ? [] : weekDays);

  cards.forEach((card) => {
    [
      { day: card.planned_work_date, kind: "予定" as const },
      { day: card.due_date, kind: "納期" as const },
    ].forEach(({ day, kind }) => {
      if (!day) return;
      if (mode === "month" && !day.startsWith(currentMonthKey)) return;
      if (mode === "week" && !visibleDaySet.has(day)) return;
      entriesByDay.set(day, [...(entriesByDay.get(day) ?? []), { card, kind }]);
    });
  });

  const firstDay = new Date(displayMonth.getFullYear(), displayMonth.getMonth(), 1);
  const daysInMonth = new Date(displayMonth.getFullYear(), displayMonth.getMonth() + 1, 0).getDate();
  const dayCells: (string | null)[] = [
    ...Array.from({ length: firstDay.getDay() }, () => null),
    ...Array.from({ length: daysInMonth }, (_, index) => `${currentMonthKey}-${pad2(index + 1)}`),
  ];
  while (dayCells.length % 7 !== 0) {
    dayCells.push(null);
  }

  function moveMonth(delta: number) {
    setDisplayMonth((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1));
  }

  function moveWeek(delta: number) {
    setDisplayWeek((current) => addDays(current, delta * 7));
  }

  const visibleCells = mode === "month" ? dayCells : weekDays;

  return (
    <section className="panel">
      <div className="calendarToolbar">
        <button onClick={() => mode === "month" ? moveMonth(-1) : moveWeek(-1)}>{mode === "month" ? "前月" : "前週"}</button>
        <h2>
          {mode === "month"
            ? `${displayMonth.getFullYear()}年 ${displayMonth.getMonth() + 1}月`
            : `${weekDays[0]}〜${weekDays[6]}`}
        </h2>
        <button onClick={() => mode === "month" ? moveMonth(1) : moveWeek(1)}>{mode === "month" ? "翌月" : "翌週"}</button>
        <div className="segmented">
          <button className={mode === "month" ? "active" : ""} onClick={() => setMode("month")}>月</button>
          <button className={mode === "week" ? "active" : ""} onClick={() => setMode("week")}>週</button>
        </div>
        <button onClick={() => {
          const today = new Date();
          setDisplayMonth(new Date(today.getFullYear(), today.getMonth(), 1));
          setDisplayWeek(mondayOfWeek(today));
        }}>今日</button>
      </div>
      <div className={mode === "month" ? "monthCalendar" : "monthCalendar weekCalendar"}>
        {weekdays.map((weekday) => (
          <div className="weekday" key={weekday}>{weekday}</div>
        ))}
        {visibleCells.map((day, index) => (
          <div className={`dayCell ${day ? "" : "empty"} ${day === todayKey ? "today" : ""}`} key={day ?? `blank-${index}`}>
            {day && (
              <>
                <div className="dayNumber">{mode === "week" ? day.slice(5) : Number(day.slice(-2))}</div>
                <div className="calendarItems">
                  {(entriesByDay.get(day) ?? []).slice(0, 4).map(({ card, kind }) => {
                    const late = kind === "納期" && day < todayKey && card.status !== "完了";
                    return (
                      <button className={`calendarItem ${kind === "予定" ? "planned" : "due"} ${late ? "late" : ""} ${isRework(card) ? "rework" : ""}`} key={`${day}-${kind}-${card.id}`} onClick={() => onOpen(card.id)}>
                        <span>{card.drawing_no}</span>
                        <small>{kind} / {card.process.name}</small>
                      </button>
                    );
                  })}
                  {(entriesByDay.get(day)?.length ?? 0) > 4 && <div className="calendarMore">+{(entriesByDay.get(day)?.length ?? 0) - 4}件</div>}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
      <div className="calendarEmptyNote">
        {visibleCells.every((day) => !day || !entriesByDay.get(day)?.length) && `この${mode === "month" ? "月" : "週"}の予定・納期はありません`}
      </div>
    </section>
  );
}
