import { FormEvent, useState } from "react";
import { request } from "../api";
import { DateField } from "./DateField";
import type { AuthUser, Card, CardDraft, Meta, WorkFormState } from "../types";
import { labelStyle, toPayload } from "../utils/card";
import { localDateString } from "../utils/date";

export function CardModal({
  card,
  meta,
  currentUser,
  onClose,
  onSaved,
}: {
  card: Card | CardDraft;
  meta: Meta;
  currentUser: AuthUser;
  onClose: () => void;
  onSaved: (id: number) => void;
}) {
  const isNew = !card.id;
  const isAdmin = currentUser.role === "admin";
  const [draft, setDraft] = useState<Card | CardDraft>(card);
  const [tagIds, setTagIds] = useState<number[]>(card.tags?.map((tag) => tag.id) ?? []);
  const [comment, setComment] = useState({ comment_type: "作業", body: "" });
  const [work, setWork] = useState<WorkFormState>({
    work_date: localDateString(),
    completed_qty_delta: 0,
    work_hours: 0,
    assignee_id: currentUser.assignee_id ?? card.assignee_id ?? meta.assignees[0]?.id ?? null,
    comment_type: "作業",
    comment: "",
  });
  const [workQtyText, setWorkQtyText] = useState("0");
  const [workHoursText, setWorkHoursText] = useState("0");
  const [error, setError] = useState("");

  async function save(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const saved = await request<Card>(isNew ? "/cards" : `/cards/${draft.id}`, {
        method: isNew ? "POST" : "PUT",
        body: JSON.stringify(toPayload(draft, tagIds)),
      });
      onSaved(saved.id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addComment(event: FormEvent) {
    event.preventDefault();
    const cardId = draft.id;
    if (isNew || !cardId) return;
    setError("");
    try {
      await request(`/cards/${cardId}/comments`, { method: "POST", body: JSON.stringify(comment) });
      setComment({ comment_type: "作業", body: "" });
      onSaved(cardId);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function addWork(event: FormEvent) {
    event.preventDefault();
    const cardId = draft.id;
    if (isNew || !cardId) return;
    setError("");
    try {
      await request(`/cards/${cardId}/work-results`, {
        method: "POST",
        body: JSON.stringify({
          ...work,
          completed_qty_delta: Number(workQtyText || 0),
          work_hours: Number(workHoursText || 0),
        }),
      });
      setWork({
        work_date: localDateString(),
        completed_qty_delta: 0,
        work_hours: 0,
        assignee_id: currentUser.assignee_id ?? draft.assignee_id ?? meta.assignees[0]?.id ?? null,
        comment_type: "作業",
        comment: "",
      });
      setWorkQtyText("0");
      setWorkHoursText("0");
      onSaved(cardId);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function update<K extends keyof CardDraft>(key: K, value: CardDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  const adminOnlyDisabled = !isAdmin;
  const workerSelectDisabled = !isAdmin;

  return (
    <div className="modalBackdrop">
      <div className="modal">
        <div className="modalHead">
          <h2>{isNew ? "カード作成" : `${card.drawing_no} 詳細`}</h2>
          <button onClick={onClose}>閉じる</button>
        </div>
        {error && <div className="error">{error}</div>}
        {!isNew && (
          <div className="detailSummary">
            <span>カード担当者: <strong>{card.assignee?.name ?? "未設定"}</strong></span>
            <span>ログイン中: <strong>{currentUser.display_name}</strong></span>
            <span>工程: <strong>{card.process?.name ?? "-"}</strong></span>
            <span>進捗: <strong>{card.completed_qty}/{card.total_qty}</strong></span>
          </div>
        )}
        {!isNew && (
          <form className="workForm priorityWorkForm" onSubmit={addWork}>
            <h3>作業実績を登録</h3>
            <DateField label="作業日" value={work.work_date} onChange={(value) => setWork({ ...work, work_date: value })} />
            <label>
              作業者
              <select value={work.assignee_id ?? ""} disabled={workerSelectDisabled} onChange={(e) => setWork({ ...work, assignee_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">未設定</option>
                {meta.assignees.map((assignee) => <option key={assignee.id} value={assignee.id}>{assignee.name}</option>)}
              </select>
            </label>
            <label>
              加工数量
              <input
                type="text"
                inputMode="numeric"
                placeholder="例: 3 / -1"
                value={workQtyText}
                onFocus={(event) => event.currentTarget.select()}
                onChange={(e) => setWorkQtyText(e.target.value)}
              />
            </label>
            <label>
              作業時間(h)
              <input
                type="text"
                inputMode="decimal"
                placeholder="例: 1.5"
                value={workHoursText}
                onFocus={(event) => event.currentTarget.select()}
                onChange={(e) => setWorkHoursText(e.target.value)}
              />
            </label>
            <label>
              コメント種別
              <select value={work.comment_type} onChange={(e) => setWork({ ...work, comment_type: e.target.value })}>
                {meta.comment_types.map((type) => <option key={type}>{type}</option>)}
              </select>
            </label>
            <label>
              コメント
              <input placeholder="マイナス入力時は理由必須" value={work.comment} onChange={(e) => setWork({ ...work, comment: e.target.value })} />
            </label>
            <button type="submit">登録</button>
          </form>
        )}
        <form className="detailGrid" onSubmit={save}>
          <h3 className="wide">基本情報</h3>
          <label>受注番号<input value={draft.order_no ?? ""} placeholder="例: E-25086" pattern="[A-Z]-[0-9]{5}" disabled={adminOnlyDisabled} onChange={(e) => update("order_no", e.target.value.toUpperCase())} /></label>
          <label>種別<input value={draft.item_type ?? ""} placeholder="例: 01" inputMode="numeric" pattern="[0-9]{2}" maxLength={2} disabled={adminOnlyDisabled} onChange={(e) => update("item_type", e.target.value.replace(/\D/g, "").slice(0, 2))} /></label>
          <label>図番<input value={draft.drawing_no} disabled={adminOnlyDisabled} onChange={(e) => update("drawing_no", e.target.value)} required /></label>
          <label>品名<input value={draft.item_name} disabled={adminOnlyDisabled} onChange={(e) => update("item_name", e.target.value)} required /></label>
          <label>総数<input type="number" min="0" value={draft.total_qty} disabled={adminOnlyDisabled} onChange={(e) => update("total_qty", Number(e.target.value))} /></label>
          <label>現在工程
            <select value={draft.current_process_id} disabled={adminOnlyDisabled} onChange={(e) => update("current_process_id", Number(e.target.value))}>
              {meta.processes.map((process) => <option key={process.id} value={process.id}>{process.name}</option>)}
            </select>
          </label>
          <label>担当者
            <select value={draft.assignee_id ?? ""} disabled={adminOnlyDisabled} onChange={(e) => update("assignee_id", e.target.value ? Number(e.target.value) : null)}>
              <option value="">未設定</option>
              {meta.assignees.map((assignee) => <option key={assignee.id} value={assignee.id}>{assignee.name}</option>)}
            </select>
          </label>
          <DateField label="作業予定日" value={draft.planned_work_date ?? ""} onChange={(value) => update("planned_work_date", value)} disabled={adminOnlyDisabled} />
          <DateField label="納期" value={draft.due_date ?? ""} onChange={(value) => update("due_date", value)} disabled={adminOnlyDisabled} />
          <fieldset className="tags">
            <legend>タグ</legend>
            {meta.tags.map((tag) => (
              <label key={tag.id} className="tagChoice">
                <input
                  type="checkbox"
                  checked={tagIds.includes(tag.id)}
                  disabled={adminOnlyDisabled}
                  onChange={(event) => {
                    setTagIds((current) => event.target.checked ? [...current, tag.id] : current.filter((id) => id !== tag.id));
                  }}
                />
                <span className="label" style={labelStyle(tag.color)}>{tag.name}</span>
              </label>
            ))}
          </fieldset>
          <label className="wide">備考<input value={draft.remarks ?? ""} disabled={adminOnlyDisabled} onChange={(e) => update("remarks", e.target.value)} /></label>
          <label className="wide">説明欄<textarea rows={6} value={draft.description} disabled={adminOnlyDisabled} onChange={(e) => update("description", e.target.value)} /></label>
          {isAdmin && <button className="primary" type="submit">保存</button>}
        </form>

        {!isNew && (
          <div className="modalSections">
            <form className="workForm" onSubmit={addComment}>
              <h3>コメント追加</h3>
              <select value={comment.comment_type} onChange={(e) => setComment({ ...comment, comment_type: e.target.value })}>
                {meta.comment_types.map((type) => <option key={type}>{type}</option>)}
              </select>
              <input value={comment.body} placeholder="コメント" onChange={(e) => setComment({ ...comment, body: e.target.value })} />
              <button type="submit">追加</button>
            </form>

            <section>
              <h3>コメント</h3>
              <div className="timeline">
                {(card.comments ?? []).map((item) => (
                  <article key={item.id}>
                    <strong>{item.comment_type}</strong>
                    <span>{item.created_at} {item.user_name ?? ""}</span>
                    <p>{item.body}</p>
                  </article>
                ))}
              </div>
            </section>

            <section>
              <h3>作業ログ</h3>
              <div className="tableScroll">
                <table>
                  <thead><tr><th>日付</th><th>担当</th><th>加工数量</th><th>時間(h)</th><th>コメント</th></tr></thead>
                  <tbody>
                    {(card.work_logs ?? []).map((log) => (
                      <tr key={log.id}>
                        <td>{log.work_date}</td>
                        <td>{log.assignee_name ?? "-"}</td>
                        <td>{log.completed_qty_delta}</td>
                        <td>{log.work_hours}</td>
                        <td>{log.comment_body ?? ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
