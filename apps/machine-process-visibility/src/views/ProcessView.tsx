import { CardTile } from "../components/CardTile";
import type { Assignee, Card, Process, ProcessSortMode } from "../types";
import { labelStyle, PROCESS_VIEW_NAMES } from "../utils/card";

export function ProcessView({
  cards,
  processes,
  assignees,
  selectedProcessId,
  sortMode,
  onSelectProcess,
  onSortModeChange,
  onOpen,
}: {
  cards: Card[];
  processes: Process[];
  assignees: Assignee[];
  selectedProcessId: number | null;
  sortMode: ProcessSortMode;
  onSelectProcess: (id: number) => void;
  onSortModeChange: (mode: ProcessSortMode) => void;
  onOpen: (id: number) => void;
}) {
  const selectableProcesses = processes.filter((process) => PROCESS_VIEW_NAMES.includes(process.name));
  const selectedProcess = selectableProcesses.find((process) => process.id === selectedProcessId) ?? selectableProcesses[0];
  const processCards = selectedProcess
    ? cards
        .filter((card) => card.current_process_id === selectedProcess.id)
        .sort((a, b) => {
          if (sortMode === "assignee") {
            const assigneeCompare = (a.assignee?.name ?? "未設定").localeCompare(b.assignee?.name ?? "未設定", "ja");
            if (assigneeCompare !== 0) return assigneeCompare;
          }
          return (a.due_date ?? "9999-12-31").localeCompare(b.due_date ?? "9999-12-31") || a.drawing_no.localeCompare(b.drawing_no);
        })
    : [];

  const groupedByAssignee = assignees
    .map((assignee) => ({
      assignee,
      cards: processCards.filter((card) => card.assignee_id === assignee.id),
    }))
    .filter((group) => group.cards.length > 0);
  const unassignedCards = processCards.filter((card) => !card.assignee_id);

  return (
    <section className="panel">
      <div className="filters">
        <label>
          工程グループ
          <select value={selectedProcess?.id ?? ""} onChange={(event) => onSelectProcess(Number(event.target.value))}>
            {selectableProcesses.map((process) => (
              <option key={process.id} value={process.id}>{process.name}</option>
            ))}
          </select>
        </label>
        <label>
          並び
          <select value={sortMode} onChange={(event) => onSortModeChange(event.target.value as ProcessSortMode)}>
            <option value="assignee">主担当ごと</option>
            <option value="due">納期順</option>
          </select>
        </label>
      </div>

      {sortMode === "assignee" ? (
        <div className="processGrid">
          {groupedByAssignee.map((group) => (
            <section className="assigneeLane" key={group.assignee.id}>
              <h2>
                <span className="dot" style={labelStyle(group.assignee.color)} /> {group.assignee.name}
              </h2>
              <div className="list">
                {group.cards.map((card) => <CardTile card={card} key={card.id} onOpen={onOpen} compact />)}
              </div>
            </section>
          ))}
          {unassignedCards.length > 0 && (
            <section className="assigneeLane">
              <h2>未設定</h2>
              <div className="list">
                {unassignedCards.map((card) => <CardTile card={card} key={card.id} onOpen={onOpen} compact />)}
              </div>
            </section>
          )}
        </div>
      ) : (
        <div className="list">
          {processCards.map((card) => <CardTile card={card} key={card.id} onOpen={onOpen} />)}
        </div>
      )}
    </section>
  );
}
