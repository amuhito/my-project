import { useState } from "react";
import type { Card } from "../types";
import { isRework } from "../utils/card";
import { localDateString, monthKey, pad2 } from "../utils/date";

export function CalendarView({ cards, onOpen }: { cards: Card[]; onOpen: (id: number) => void }) {
  const [displayMonth, setDisplayMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });
  const todayKey = localDateString();
  const currentMonthKey = monthKey(displayMonth);
  const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
  const entriesByDay = new Map<string, { card: Card; kind: "予定" | "納期" }[]>();

  cards.forEach((card) => {
    [
      { day: card.planned_work_date, kind: "予定" as const },
      { day: card.due_date, kind: "納期" as const },
    ].forEach(({ day, kind }) => {
      if (!day || !day.startsWith(currentMonthKey)) return;
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

  return (
    <section className="panel">
      <div className="calendarToolbar">
        <button onClick={() => moveMonth(-1)}>前月</button>
        <h2>{displayMonth.getFullYear()}年 {displayMonth.getMonth() + 1}月</h2>
        <button onClick={() => moveMonth(1)}>翌月</button>
        <button onClick={() => setDisplayMonth(new Date(new Date().getFullYear(), new Date().getMonth(), 1))}>今月</button>
      </div>
      <div className="monthCalendar">
        {weekdays.map((weekday) => (
          <div className="weekday" key={weekday}>{weekday}</div>
        ))}
        {dayCells.map((day, index) => (
          <div className={`dayCell ${day ? "" : "empty"} ${day === todayKey ? "today" : ""}`} key={day ?? `blank-${index}`}>
            {day && (
              <>
                <div className="dayNumber">{Number(day.slice(-2))}</div>
                <div className="calendarItems">
                  {(entriesByDay.get(day) ?? []).map(({ card, kind }) => (
                    <button className={`calendarItem ${isRework(card) ? "rework" : ""}`} key={`${day}-${kind}-${card.id}`} onClick={() => onOpen(card.id)}>
                      <span>{card.drawing_no}</span>
                      <small>{kind} / {card.process.name}</small>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
      <div className="calendarEmptyNote">
        {dayCells.every((day) => !day || !entriesByDay.get(day)?.length) && "この月の予定・納期はありません"}
      </div>
    </section>
  );
}
