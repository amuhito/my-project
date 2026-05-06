import { useEffect, useState } from "react";
import { confirmDrawingReady, updateInquiryItem } from "../api";
import { INQUIRY_ITEM_DATE_FIELD_LABELS } from "../constants";
import type { InquiryItemDetail } from "../types";
import { PROCESS_OPTIONS } from "../utils/inquiryDisplay";

type InquiryItemModalProps = {
  item: InquiryItemDetail | null;
  open: boolean;
  onClose: () => void;
  onSaved: (item: InquiryItemDetail) => void;
};

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
  const [finalArrivalPlannedDate, setFinalArrivalPlannedDate] = useState("");
  const [finalHandoverDate, setFinalHandoverDate] = useState("");
  const [assemblyCompletedDate, setAssemblyCompletedDate] = useState("");
  const [packingCompletedDate, setPackingCompletedDate] = useState("");
  const [shippingPlannedDate, setShippingPlannedDate] = useState("");
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
    setFinalArrivalPlannedDate(toDateInput(item.final_arrival_planned_date));
    setFinalHandoverDate(toDateInput(item.final_handover_date));
    setAssemblyCompletedDate(toDateInput(item.assembly_completed_date));
    setPackingCompletedDate(toDateInput(item.packing_completed_date));
    setShippingPlannedDate(toDateInput(item.shipping_planned_date));
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
        // Canonical domain fields (new)
        final_arrival_planned_date: finalArrivalPlannedDate || null,
        final_handover_date: finalHandoverDate || null,
        assembly_completed_date: assemblyCompletedDate || null,
        packing_completed_date: packingCompletedDate || null,
        shipping_planned_date: shippingPlannedDate || null,
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
          <h2>子案件編集 {item.item_no}</h2>
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

        <div className="row-fields row-fields-5">
          <label className="field">
            <span>{INQUIRY_ITEM_DATE_FIELD_LABELS.final_arrival_planned_date}</span>
            <input
              type="date"
              value={finalArrivalPlannedDate}
              onChange={(event) => setFinalArrivalPlannedDate(event.target.value)}
            />
          </label>
          <label className="field">
            <span>{INQUIRY_ITEM_DATE_FIELD_LABELS.final_handover_date}</span>
            <input
              type="date"
              value={finalHandoverDate}
              onChange={(event) => setFinalHandoverDate(event.target.value)}
            />
          </label>
          <label className="field">
            <span>{INQUIRY_ITEM_DATE_FIELD_LABELS.assembly_completed_date}</span>
            <input
              type="date"
              value={assemblyCompletedDate}
              onChange={(event) => setAssemblyCompletedDate(event.target.value)}
            />
          </label>
          <label className="field">
            <span>{INQUIRY_ITEM_DATE_FIELD_LABELS.packing_completed_date}</span>
            <input
              type="date"
              value={packingCompletedDate}
              onChange={(event) => setPackingCompletedDate(event.target.value)}
            />
          </label>
          <label className="field">
            <span>{INQUIRY_ITEM_DATE_FIELD_LABELS.shipping_planned_date}</span>
            <input
              type="date"
              value={shippingPlannedDate}
              onChange={(event) => setShippingPlannedDate(event.target.value)}
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
