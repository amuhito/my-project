import { useEffect, useState } from "react";
import { confirmDrawingReady, updateInquiryItem } from "../api";
import type { InquiryItemDetail } from "../types";

type InquiryItemModalProps = {
  item: InquiryItemDetail | null;
  open: boolean;
  onClose: () => void;
  onSaved: (item: InquiryItemDetail) => void;
};

const PROCESS_OPTIONS = [
  { value: "not_drawn", label: "未出図" },
  { value: "arranging", label: "手配中" },
  { value: "arrival_receiving", label: "入荷・受入" },
  { value: "internal_processing", label: "内部処理" },
  { value: "shipped", label: "発送完了" },
] as const;

const STATE_OPTIONS = [
  { value: "normal", label: "通常" },
  { value: "waiting", label: "待ち" },
  { value: "done", label: "完了" },
] as const;

function toDateInput(value: string | null): string {
  return value ?? "";
}

function isUnauthorizedError(error: unknown) {
  return error instanceof Error && error.message === "UNAUTHORIZED";
}

export function InquiryItemModal({ item, open, onClose, onSaved }: InquiryItemModalProps) {
  const [process, setProcess] = useState<InquiryItemDetail["process"]>("not_drawn");
  const [owner, setOwner] = useState("");
  const [state, setState] = useState<InquiryItemDetail["state"]>("normal");
  const [plannedArrivalDate, setPlannedArrivalDate] = useState("");
  const [actualArrivalDate, setActualArrivalDate] = useState("");
  const [packingDueDate, setPackingDueDate] = useState("");
  const [confirmedShippingDate, setConfirmedShippingDate] = useState("");
  const [remarks, setRemarks] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!item) {
      return;
    }
    setProcess(item.process);
    setOwner(item.owner);
    setState(item.state);
    setPlannedArrivalDate(toDateInput(item.planned_arrival_date));
    setActualArrivalDate(toDateInput(item.actual_arrival_date));
    setPackingDueDate(toDateInput(item.packing_due_date));
    setConfirmedShippingDate(toDateInput(item.confirmed_shipping_date));
    setRemarks(item.remarks ?? "");
    setError("");
  }, [item]);

  if (!open || !item) {
    return null;
  }

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const updated = await updateInquiryItem(item.id, {
        process,
        owner,
        state,
        planned_arrival_date: plannedArrivalDate || null,
        actual_arrival_date: actualArrivalDate || null,
        packing_due_date: packingDueDate || null,
        confirmed_shipping_date: confirmedShippingDate || null,
        remarks,
      });
      onSaved(updated);
    } catch (saveError) {
      if (isUnauthorizedError(saveError)) {
        setError("セッションが切れました。再ログインしてください。");
      } else {
        setError(saveError instanceof Error ? saveError.message : "保存に失敗しました。");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmDrawing = async () => {
    setSaving(true);
    setError("");
    try {
      const updated = await confirmDrawingReady(item.id);
      onSaved(updated);
    } catch (saveError) {
      if (isUnauthorizedError(saveError)) {
        setError("セッションが切れました。再ログインしてください。");
      } else {
        setError(saveError instanceof Error ? saveError.message : "出図済み更新に失敗しました。");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h2>
            子案件編集 {item.item_type}-{item.item_no.split("-")[1] ?? item.item_no}
          </h2>
          <button className="ghost-button" onClick={onClose} type="button">
            閉じる
          </button>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}

        <div className="row-fields row-fields-3">
          <label className="field">
            <span>工程</span>
            <select value={process} onChange={(event) => setProcess(event.target.value as InquiryItemDetail["process"])}>
              {PROCESS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>担当</span>
            <input value={owner} onChange={(event) => setOwner(event.target.value)} />
          </label>
          <label className="field">
            <span>状態</span>
            <select value={state} onChange={(event) => setState(event.target.value as InquiryItemDetail["state"])}>
              {STATE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="row-fields row-fields-4">
          <label className="field">
            <span>入荷予定日</span>
            <input
              type="date"
              value={plannedArrivalDate}
              onChange={(event) => setPlannedArrivalDate(event.target.value)}
            />
          </label>
          <label className="field">
            <span>入荷日</span>
            <input
              type="date"
              value={actualArrivalDate}
              onChange={(event) => setActualArrivalDate(event.target.value)}
            />
          </label>
          <label className="field">
            <span>梱包納期</span>
            <input type="date" value={packingDueDate} onChange={(event) => setPackingDueDate(event.target.value)} />
          </label>
          <label className="field">
            <span>確定納期</span>
            <input
              type="date"
              value={confirmedShippingDate}
              onChange={(event) => setConfirmedShippingDate(event.target.value)}
            />
          </label>
        </div>

        <label className="field">
          <span>備考</span>
          <textarea rows={4} value={remarks} onChange={(event) => setRemarks(event.target.value)} />
        </label>

        <div className="row-fields">
          <button
            className="secondary-button"
            disabled={saving || item.drawing_ready_confirmed}
            onClick={() => void handleConfirmDrawing()}
            type="button"
          >
            {item.drawing_ready_confirmed ? "出図済み確認済み" : "出図済みにして手配開始"}
          </button>
          <button className="primary-button" disabled={saving} onClick={() => void handleSave()} type="button">
            {saving ? "保存中..." : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
