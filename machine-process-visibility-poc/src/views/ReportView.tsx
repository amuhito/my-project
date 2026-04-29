import { useEffect, useState } from "react";
import { API, getToken, request } from "../api";
import { DateField } from "../components/DateField";
import type { Meta, ReportRow } from "../types";
import { localDateString } from "../utils/date";

export function ReportView({ meta }: { meta: Meta }) {
  const today = localDateString();
  const [workDate, setWorkDate] = useState(today);
  const [assigneeId, setAssigneeId] = useState("");
  const [processId, setProcessId] = useState("");
  const [rows, setRows] = useState<ReportRow[]>([]);
  const [error, setError] = useState("");
  const totalQty = rows.reduce((sum, row) => sum + Number(row.completed_qty_delta), 0);
  const totalHours = rows.reduce((sum, row) => sum + Number(row.work_hours), 0);
  const assigneeTotals = groupTotals(rows, "assignee_name");
  const processTotals = groupTotals(rows, "process_name");

  function dailyReportQuery() {
    const params = new URLSearchParams({ work_date: workDate });
    if (assigneeId) params.set("assignee_id", assigneeId);
    if (processId) params.set("process_id", processId);
    return params.toString();
  }

  async function search() {
    setError("");
    try {
      setRows(await request<ReportRow[]>(`/reports/daily?${dailyReportQuery()}`));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function exportCsv() {
    setError("");
    const token = getToken();
    const res = await fetch(`${API}/reports/daily.csv?${dailyReportQuery()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: "CSV出力に失敗しました" }));
      setError(detail.detail ?? "CSV出力に失敗しました");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `daily_report_${workDate}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    search();
  }, []);

  return (
    <section className="panel">
      <div className="filters">
        <DateField value={workDate} onChange={setWorkDate} />
        <select value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)}>
          <option value="">全担当者</option>
          {meta.assignees.map((assignee) => (
            <option key={assignee.id} value={assignee.id}>{assignee.name}</option>
          ))}
        </select>
        <select value={processId} onChange={(event) => setProcessId(event.target.value)}>
          <option value="">全工程</option>
          {meta.processes.map((process) => (
            <option key={process.id} value={process.id}>{process.name}</option>
          ))}
        </select>
        <button onClick={search}>検索</button>
        <button onClick={exportCsv}>CSV</button>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="summaryGrid">
        <div><strong>{rows.length}</strong><span>件</span></div>
        <div><strong>{totalQty}</strong><span>完了数</span></div>
        <div><strong>{totalHours.toFixed(2)}</strong><span>時間</span></div>
      </div>
      <div className="subtotalGrid">
        <section>
          <h3>担当者別小計</h3>
          {assigneeTotals.map((item) => <p key={item.name}>{item.name || "未設定"}: {item.qty} / {item.hours.toFixed(2)}h</p>)}
        </section>
        <section>
          <h3>工程別小計</h3>
          {processTotals.map((item) => <p key={item.name}>{item.name || "未設定"}: {item.qty} / {item.hours.toFixed(2)}h</p>)}
        </section>
      </div>
      <div className="tableScroll">
        <table className="report">
          <thead>
            <tr>
              <th>日付</th>
              <th>作業者</th>
              <th>登録者</th>
              <th>工程</th>
              <th>受注番号</th>
              <th>種別</th>
              <th>図番</th>
              <th>品名</th>
              <th>今回完了数</th>
              <th>作業時間</th>
              <th>コメント種別</th>
              <th>コメント</th>
              <th>異常・気づき</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                <td>{row.work_date}</td>
                <td>{row.assignee_name}</td>
                <td>{row.registered_by_name ?? "-"}</td>
                <td>{row.process_name}</td>
                <td>{row.order_no}</td>
                <td>{row.item_type}</td>
                <td>{row.drawing_no}</td>
                <td>{row.item_name}</td>
                <td>{row.completed_qty_delta}</td>
                <td>{row.work_hours}</td>
                <td>{row.comment_type}</td>
                <td>{row.comment}</td>
                <td>{row.finding}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function groupTotals(rows: ReportRow[], key: "assignee_name" | "process_name") {
  const totals = new Map<string, { name: string; qty: number; hours: number }>();
  rows.forEach((row) => {
    const name = row[key] ?? "";
    const current = totals.get(name) ?? { name, qty: 0, hours: 0 };
    current.qty += Number(row.completed_qty_delta);
    current.hours += Number(row.work_hours);
    totals.set(name, current);
  });
  return [...totals.values()].sort((a, b) => a.name.localeCompare(b.name, "ja"));
}
