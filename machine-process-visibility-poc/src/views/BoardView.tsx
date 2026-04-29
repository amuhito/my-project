import { DragEvent, useState } from "react";
import { CardTile } from "../components/CardTile";
import type { Card, Process } from "../types";

export function BoardView({
  cards,
  processes,
  onOpen,
  onMove,
  canMove,
}: {
  cards: Card[];
  processes: Process[];
  onOpen: (id: number) => void;
  onMove: (card: Card, process: Process) => void;
  canMove: boolean;
}) {
  const [draggingCardId, setDraggingCardId] = useState<number | null>(null);
  const [dropProcessId, setDropProcessId] = useState<number | null>(null);

  function handleDrop(event: DragEvent<HTMLDivElement>, process: Process) {
    event.preventDefault();
    setDropProcessId(null);
    if (!canMove) return;
    const cardId = Number(event.dataTransfer.getData("text/plain"));
    const card = cards.find((item) => item.id === cardId);
    if (card) onMove(card, process);
  }

  return (
    <section className="board">
      {processes.map((process) => {
        const processCards = cards.filter((card) => card.current_process_id === process.id);
        return (
          <div
            className={`column ${dropProcessId === process.id ? "dropTarget" : ""}`}
            key={process.id}
            onDragOver={(event) => {
              if (!canMove) return;
              event.preventDefault();
              setDropProcessId(process.id);
            }}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                setDropProcessId(null);
              }
            }}
            onDrop={(event) => handleDrop(event, process)}
          >
            <div className="columnHeader">
              <h2>{process.name}</h2>
              <span>{processCards.length}</span>
            </div>
            <div className="columnList">
              {processCards.map((card) => (
                <CardTile
                  card={card}
                  key={card.id}
                  onOpen={onOpen}
                  draggable={canMove}
                  dragging={draggingCardId === card.id}
                  onDragStart={() => setDraggingCardId(card.id)}
                  onDragEnd={() => {
                    setDraggingCardId(null);
                    setDropProcessId(null);
                  }}
                />
              ))}
            </div>
          </div>
        );
      })}
    </section>
  );
}
