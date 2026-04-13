import { useEffect, useMemo, useState } from "react";
import { addComment, saveCard } from "../api";
import { ARCHIVABLE_STATUS } from "../constants";
import type { CardDetail, ChecklistItem } from "../types";

type CardModalProps = {
  card: CardDetail | null;
  open: boolean;
  onClose: () => void;
  onSaved: (updatedCard: CardDetail) => void;
  onArchiveToggle: (cardId: number, archived: boolean) => void;
  statuses: string[];
};

type EditableChecklistItem = ChecklistItem & { tempKey: string };

type TimelineItem =
  | {
      id: string;
      kind: "comment";
      author: string;
      body: string;
      createdAt: string;
    }
  | {
      id: string;
      kind: "activity";
      message: string;
      createdAt: string;
    };

function todayText() {
  return new Date().toISOString().slice(0, 10);
}

function canArchiveCard(params: {
  archived: boolean;
  status: string;
  requestedDueDate: string;
}) {
  if (params.archived) {
    return true;
  }

  return (
    params.status === ARCHIVABLE_STATUS &&
    !!params.requestedDueDate &&
    params.requestedDueDate < todayText()
  );
}

function toEditableItems(items: ChecklistItem[]): EditableChecklistItem[] {
  return items.map((item) => ({
    ...item,
    tempKey: `saved-${item.id}`,
  }));
}

function getInitials(text: string) {
  return text.trim().slice(0, 2).toUpperCase() || "AI";
}

export function CardModal({
  card,
  open,
  onClose,
  onSaved,
  onArchiveToggle,
  statuses,
}: CardModalProps) {
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
  const [activityVisible, setActivityVisible] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [saveError, setSaveError] = useState("");

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
    setActivityVisible(false);
    setMenuOpen(false);
    setSaveError("");
  }, [card]);

  const timelineItems = useMemo<TimelineItem[]>(() => {
    if (!card) {
      return [];
    }

    const commentItems: TimelineItem[] = card.comments.map((comment) => ({
      id: `comment-${comment.id}`,
      kind: "comment",
      author: comment.author,
      body: comment.body,
      createdAt: comment.created_at,
    }));

    const activityItems: TimelineItem[] = activityVisible
      ? card.activities.map((activity) => ({
          id: `activity-${activity.id}`,
          kind: "activity",
          message: activity.message,
          createdAt: activity.created_at,
        }))
      : [];

    return [...commentItems, ...activityItems].sort((left, right) =>
      right.createdAt.localeCompare(left.createdAt),
    );
  }, [activityVisible, card]);

  if (!open || !card) {
    return null;
  }

  const archiveEnabled = canArchiveCard({
    archived: card.archived,
    status,
    requestedDueDate,
  });

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
    setSaveError("");
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
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "保存に失敗しました。");
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
    <div
      className="modal-backdrop"
      onClick={() => {
        setMenuOpen(false);
        onClose();
      }}
    >
      <div
        className="modal-card"
        onClick={(event) => {
          event.stopPropagation();
          setMenuOpen(false);
        }}
      >
        <div className="modal-header">
          <div>
            <div className="modal-eyebrow">案件詳細</div>
            <h2>{[projectNo, customerName].filter(Boolean).join(" ") || "新しい案件"}</h2>
          </div>
          <div className="modal-actions">
            <div className="modal-menu-wrap">
              <button
                aria-label="カードメニュー"
                className="icon-button"
                onClick={(event) => {
                  event.stopPropagation();
                  setMenuOpen((current) => !current);
                }}
                type="button"
              >
                ...
              </button>
              {menuOpen ? (
                <div
                  className="modal-menu"
                  onClick={(event) => event.stopPropagation()}
                >
                  <button
                    className="modal-menu-item danger"
                    disabled={!archiveEnabled}
                    onClick={() => {
                      setMenuOpen(false);
                      onArchiveToggle(card.id, card.archived);
                    }}
                    type="button"
                  >
                    {card.archived ? "アーカイブ解除" : "アーカイブ"}
                  </button>
                </div>
              ) : null}
            </div>
            <button className="ghost-button" onClick={onClose} type="button">
              閉じる
            </button>
          </div>
        </div>

        <div className="modal-grid modal-grid-wide">
          <section className="modal-main">
            {saveError ? <div className="error-banner">{saveError}</div> : null}
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
                <span>最短◎発送日</span>
                <input
                  type="date"
                  value={earliestShipDate}
                  onChange={(event) => setEarliestShipDate(event.target.value)}
                />
              </label>
            </div>

            <div className="row-fields row-fields-2">
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
                  placeholder="例: 発送日確認, 外注先"
                  value={labels}
                  onChange={(event) => setLabels(event.target.value)}
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
                  項目を追加
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
                      className="ghost-button"
                      onClick={() => handleChecklistRemove(item.tempKey)}
                      type="button"
                    >
                      削除
                    </button>
                  </div>
                ))}
              </div>
            </section>

            <div className="modal-footer">
              <button className="ghost-button" onClick={onClose} type="button">
                キャンセル
              </button>
              <button className="primary-button" disabled={saving} onClick={() => void handleSave()} type="button">
                {saving ? "保存中..." : "保存"}
              </button>
            </div>
          </section>

          <aside className="modal-side modal-side-timeline">
            <section className="panel panel-timeline">
              <div className="panel-header">
                <h3>コメントとアクティビティ</h3>
                <button
                  className="ghost-button small"
                  onClick={() => setActivityVisible((current) => !current)}
                  type="button"
                >
                  {activityVisible ? "詳細を隠す" : "詳細を表示"}
                </button>
              </div>

              <div className="comment-composer">
                <textarea
                  placeholder="コメントを入力してください"
                  rows={3}
                  value={commentDraft}
                  onChange={(event) => setCommentDraft(event.target.value)}
                />
                <button
                  className="secondary-button"
                  disabled={saving || !commentDraft.trim()}
                  onClick={() => void handleAddComment()}
                  type="button"
                >
                  コメントする
                </button>
              </div>

              <div className="timeline-list">
                {timelineItems.map((item) => (
                  <div
                    className={`timeline-item ${item.kind === "activity" ? "timeline-item-activity" : ""}`}
                    key={item.id}
                  >
                    <div className="timeline-avatar">
                      {item.kind === "comment" ? getInitials(item.author) : "記録"}
                    </div>
                    <div className="timeline-content">
                      <div className="timeline-meta">
                        <strong>
                          {item.kind === "comment" ? `${item.author}さんがコメントしました` : item.message}
                        </strong>
                        <span>{item.createdAt}</span>
                      </div>
                      {item.kind === "comment" ? (
                        <div className="timeline-body timeline-body-comment">{item.body}</div>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
