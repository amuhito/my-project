import type { DragEventHandler } from "react";
import type { Card } from "../types";
import { isRework, labelStyle, percent } from "../utils/card";

export function CardTile({
  card,
  onOpen,
  compact = false,
  draggable = false,
  dragging = false,
  onDragStart,
  onDragEnd,
}: {
  card: Card;
  onOpen: (id: number) => void;
  compact?: boolean;
  draggable?: boolean;
  dragging?: boolean;
  onDragStart?: () => void;
  onDragEnd?: () => void;
}) {
  const handleDragStart: DragEventHandler<HTMLButtonElement> = (event) => {
    if (!draggable) return;
    event.dataTransfer.setData("text/plain", String(card.id));
    event.dataTransfer.effectAllowed = "move";
    onDragStart?.();
  };

  return (
    <button
      className={`card ${isRework(card) ? "rework" : ""} ${dragging ? "dragging" : ""}`}
      draggable={draggable}
      onClick={() => onOpen(card.id)}
      onDragStart={handleDragStart}
      onDragEnd={onDragEnd}
    >
      {card.tags.length > 0 && (
        <div className="cardLabels">
          {card.tags.map((tag) => <span className="tagStrip" style={labelStyle(tag.color)} key={tag.id}>{tag.name}</span>)}
        </div>
      )}
      <div className="cardHead">
        <div>
          <strong>{card.drawing_no}</strong>
          <p>{card.item_name}</p>
        </div>
        <span>{card.status}</span>
      </div>
      {(card.order_no || card.item_type) && (
        <div className="subMeta">
          {card.order_no && <span>受注 {card.order_no}</span>}
          {card.item_type && <span>{card.item_type}</span>}
        </div>
      )}
      {card.remarks && <p className="remarksLine">{card.remarks}</p>}
      <div className="progress">
        <div style={{ width: `${card.progress_rate}%` }} />
      </div>
      <div className="cardFooter">
        {card.assignee ? (
          <span className="avatar" style={labelStyle(card.assignee.color)} title={card.assignee.name}>
            {card.assignee.name.slice(0, 1)}
          </span>
        ) : (
          <span className="avatar empty">?</span>
        )}
        <span>{percent(card)}</span>
      </div>
      <div className="metaLine">
        {!compact && <span>予定 {card.planned_work_date ?? "-"}</span>}
        <span>納期 {card.due_date ?? "-"}</span>
      </div>
    </button>
  );
}
