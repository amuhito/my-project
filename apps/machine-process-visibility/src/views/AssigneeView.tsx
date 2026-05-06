import type { Assignee, Card } from "../types";
import { labelStyle } from "../utils/card";

export function AssigneeView({ cards, assignees, onOpen }: { cards: Card[]; assignees: Assignee[]; onOpen: (id: number) => void }) {
  return (
    <div className="processGrid">
      {assignees.map((assignee) => (
        <section className="panel" key={assignee.id}>
          <h2>
            <span className="dot" style={labelStyle(assignee.color)} /> {assignee.name}
          </h2>
          <div className="tableScroll">
            <table>
              <thead>
                <tr>
                  <th>図番</th>
                  <th>予定</th>
                  <th>進捗</th>
                  <th>納期</th>
                </tr>
              </thead>
              <tbody>
                {cards
                  .filter((card) => card.assignee_id === assignee.id)
                  .map((card) => (
                    <tr key={card.id} onClick={() => onOpen(card.id)}>
                      <td>{card.drawing_no}</td>
                      <td>{card.planned_work_date ?? "-"}</td>
                      <td>{card.progress_rate}%</td>
                      <td>{card.due_date ?? "-"}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}
