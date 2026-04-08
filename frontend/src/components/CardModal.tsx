import { useEffect, useState } from "react";
import { addComment, saveCard } from "../api";
import type { CardDetail, ChecklistItem } from "../types";

type CardModalProps = {
  card: CardDetail | null;
  open: boolean;
  onClose: () => void;
  onSaved: (updatedCard: CardDetail) => void;
  statuses: string[];
};

type EditableChecklistItem = ChecklistItem & { tempKey: string };

function toEditableItems(items: ChecklistItem[]): EditableChecklistItem[] {
  return items.map((item) => ({
    ...item,
    tempKey: `saved-${item.id}`,
  }));
}

export function CardModal({ card, open, onClose, onSaved, statuses }: CardModalProps) {
  const [projectNo, setProjectNo] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [status, setStatus] = useState("");
  const [receivedDate, setReceivedDate] = useState("");
  const [requestedDueDate, setRequestedDueDate] = useState("");
  const [assigneeName, setAssigneeName] = useState("");
  const [responseDueDate, setResponseDueDate] = useState("");
  const [earliestShipDate, setEarliestShipDate] = useState("");
  const [notes, setNotes] = useState("");
  const [labels, setLabels] = useState("");
  const [checklist, setChecklist] = useState<EditableChecklistItem[]>([]);
  const [commentDraft, setCommentDraft] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!card) {
      return;
    }
    setProjectNo(card.project_no);
    setCustomerName(card.customer_name);
    setStatus(card.status);
    setReceivedDate(card.received_date ?? "");
    setRequestedDueDate(card.requested_due_date ?? "");
    setAssigneeName(card.assignee_name);
    setResponseDueDate(card.response_due_date ?? "");
    setEarliestShipDate(card.earliest_ship_date ?? "");
    setNotes(card.notes);
    setLabels(card.labels.join(", "));
    setChecklist(toEditableItems(card.checklist));
    setCommentDraft("");
  }, [card]);

  if (!open || !card) {
    return null;
  }

  const handleChecklistText = (tempKey: string, text: string) => {
    setChecklist((current) =>
      current.map((item) => (item.tempKey === tempKey ? { ...item, text } : item)),
    );
  };

  const handleChecklistToggle = (tempKey: string) => {
    setChecklist((current) =>
      current.map((item) =>
        item.tempKey === tempKey ? { ...item, completed: !item.completed } : item,
      ),
    );
  };

  const handleChecklistRemove = (tempKey: string) => {
    setChecklist((current) => current.filter((item) => item.tempKey !== tempKey));
  };

  const handleChecklistAdd = () => {
    setChecklist((current) => [
      ...current,
      {
        id: 0,
        text: "",
        completed: false,
        position: current.length,
        tempKey: `new-${Date.now()}`,
      },
    ]);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await saveCard(card.id, {
        title: [projectNo, customerName].filter(Boolean).join(" "),
        project_no: projectNo,
        customer_name: customerName,
        status,
        received_date: receivedDate || null,
        requested_due_date: requestedDueDate || null,
        assignee_name: assigneeName,
        response_due_date: responseDueDate || null,
        earliest_ship_date: earliestShipDate || null,
        description: "",
        notes,
        history_text: "",
        labels: labels
          .split(",")
          .map((label) => label.trim())
          .filter(Boolean),
        checklist: checklist
          .filter((item) => item.text.trim())
          .map((item, index) => ({
            id: item.id || null,
            text: item.text,
            completed: item.completed,
            position: index,
          })),
      });
      onSaved(updated);
    } finally {
      setSaving(false);
    }
  };

  const handleAddComment = async () => {
    if (!commentDraft.trim()) {
      return;
    }
    setSaving(true);
    try {
      const updated = await addComment(card.id, commentDraft);
      onSaved(updated);
      setCommentDraft("");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-eyebrow">案件詳細</div>
            <h2>{[projectNo, customerName].filter(Boolean).join(" ") || "新規案件"}</h2>
          </div>
          <button className="ghost-button" onClick={onClose} type="button">
            閉じる
          </button>
        </div>

        <div className="modal-grid">
          <section className="modal-main">
            <div className="row-fields row-fields-3">
              <label className="field">
                <span>受注番号</span>
                <input value={projectNo} onChange={(event) => setProjectNo(event.target.value)} />
              </label>
              <label className="field">
                <span>ユーザー様</span>
                <input
                  value={customerName}
                  onChange={(event) => setCustomerName(event.target.value)}
                />
              </label>
              <label className="field">
                <span>ステータス</span>
                <select value={status} onChange={(event) => setStatus(event.target.value)}>
                  {statuses.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="row-fields row-fields-4">
              <label className="field">
                <span>日付</span>
                <input
                  type="date"
                  value={receivedDate}
                  onChange={(event) => setReceivedDate(event.target.value)}
                />
              </label>
              <label className="field">
                <span>希望納期</span>
                <input
                  type="date"
                  value={requestedDueDate}
                  onChange={(event) => setRequestedDueDate(event.target.value)}
                />
              </label>
              <label className="field">
                <span>回答納期</span>
                <input
                  type="date"
                  value={responseDueDate}
                  onChange={(event) => setResponseDueDate(event.target.value)}
                />
              </label>
              <label className="field">
                <span>最短の発送日</span>
                <input
                  type="date"
                  value={earliestShipDate}
                  onChange={(event) => setEarliestShipDate(event.target.value)}
                />
              </label>
            </div>

            <div className="row-fields">
              <label className="field">
                <span>確認先</span>
                <input
                  value={assigneeName}
                  onChange={(event) => setAssigneeName(event.target.value)}
                />
              </label>
              <label className="field">
                <span>ラベル</span>
                <input
                  value={labels}
                  onChange={(event) => setLabels(event.target.value)}
                  placeholder="例: 発送日確認, 外注先"
                />
              </label>
            </div>

            <label className="field">
              <span>備考（理由）</span>
              <textarea rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} />
            </label>
            <section className="panel">
              <div className="panel-header">
                <h3>チェックリスト</h3>
                <button className="secondary-button" onClick={handleChecklistAdd} type="button">
                  項目追加
                </button>
              </div>
              <div className="checklist-list">
                {checklist.map((item) => (
                  <div className="checklist-row" key={item.tempKey}>
                    <input
                      checked={item.completed}
                      onChange={() => handleChecklistToggle(item.tempKey)}
                      type="checkbox"
                    />
                    <input
                      className="checklist-input"
                      value={item.text}
                      onChange={(event) => handleChecklistText(item.tempKey, event.target.value)}
                    />
                    <button
                      className="ghost-button small"
                      onClick={() => handleChecklistRemove(item.tempKey)}
                      type="button"
                    >
                      削除
                    </button>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <h3>コメント</h3>
              </div>
              <div className="comment-composer">
                <textarea
                  rows={3}
                  value={commentDraft}
                  onChange={(event) => setCommentDraft(event.target.value)}
                  placeholder="コメントを入力"
                />
                <button className="primary-button" onClick={handleAddComment} type="button">
                  コメント追加
                </button>
              </div>
              <div className="stack-list">
                {card.comments.map((comment) => (
                  <article className="stack-item" key={comment.id}>
                    <div className="stack-item-header">
                      <strong>{comment.author}</strong>
                      <span>{comment.created_at}</span>
                    </div>
                    <p>{comment.body}</p>
                  </article>
                ))}
              </div>
            </section>
          </section>

          <aside className="modal-side">
            <section className="panel">
              <div className="panel-header">
                <h3>アクティビティ</h3>
              </div>
              <div className="stack-list">
                {card.activities.map((activity) => (
                  <article className="stack-item" key={activity.id}>
                    <div className="stack-item-header">
                      <strong>{activity.message}</strong>
                      <span>{activity.created_at}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </aside>
        </div>

        <div className="modal-footer">
          <button className="ghost-button" onClick={onClose} type="button">
            キャンセル
          </button>
          <button className="primary-button" disabled={saving} onClick={handleSave} type="button">
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
