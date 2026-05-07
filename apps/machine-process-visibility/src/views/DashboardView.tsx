import { useEffect, useMemo, useState } from "react";
import { request } from "../api";
import type { DashboardAssigneeSummary, DashboardPeriod, DashboardResponse } from "../types";
import { localDateString, minutesLabel } from "../utils/date";

export function DashboardView() {
  const [period, setPeriod] = useState<DashboardPeriod>("month");
  const [baseDate, setBaseDate] = useState(localDateString());
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [selectedAssigneeId, setSelectedAssigneeId] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    request<DashboardResponse>(`/dashboard/workload?period=${period}&base_date=${baseDate}`)
      .then((result) => {
        setData(result);
        setSelectedAssigneeId((current) => current ?? result.summaries[0]?.assignee.id ?? null);
      })
      .catch((err) => setError((err as Error).message));
  }, [period, baseDate]);

  const selected = useMemo<DashboardAssigneeSummary | null>(
    () => data?.summaries.find((summary) => summary.assignee.id === selectedAssigneeId) ?? data?.summaries[0] ?? null,
    [data, selectedAssigneeId],
  );
  const totals = useMemo(() => {
    const summaries = data?.summaries ?? [];
    return {
      work_count: summaries.reduce((sum, item) => sum + item.work_count, 0),
      completed_qty: summaries.reduce((sum, item) => sum + item.completed_qty, 0),
      actual_minutes: summaries.reduce((sum, item) => sum + item.actual_minutes, 0),
      estimated_minutes: summaries.reduce((sum, item) => sum + item.estimated_minutes, 0),
    };
  }, [data]);

  return (
    <section className="panel dashboard">
      <div className="dashboardToolbar">
        <div>
          <h2>実績ダッシュボード</h2>
          <p>{data ? `${data.label} (${data.start_date}〜${data.end_date})` : "集計中"}</p>
        </div>
        <div className="segmented">
          <button className={period === "month" ? "active" : ""} onClick={() => setPeriod("month")}>月次</button>
          <button className={period === "week" ? "active" : ""} onClick={() => setPeriod("week")}>週次</button>
        </div>
        <input type="date" value={baseDate} onChange={(event) => setBaseDate(event.target.value)} />
      </div>
      {error && <div className="error">{error}</div>}
      {data && (
        <>
          <div className="summaryStrip">
            <span>作業件数 <strong>{totals.work_count}</strong></span>
            <span>加工数量 <strong>{totals.completed_qty}</strong></span>
            <span>実績 <strong>{minutesLabel(totals.actual_minutes)}</strong></span>
            <span>見積 <strong>{minutesLabel(totals.estimated_minutes)}</strong></span>
            <span>差分 <strong>{minutesLabel(totals.estimated_minutes - totals.actual_minutes)}</strong></span>
          </div>
          <div className="assigneeMetrics">
            {data.summaries.map((summary) => (
              <button
                key={summary.assignee.id}
                className={summary.assignee.id === selectedAssigneeId ? "active metricCard" : "metricCard"}
                onClick={() => setSelectedAssigneeId(summary.assignee.id)}
              >
                <span className="assigneeDot" style={{ backgroundColor: summary.assignee.color }} />
                <strong>{summary.assignee.name}</strong>
                <small>作業 {summary.work_count}件 / 数量 {summary.completed_qty}</small>
                <span>実績 {minutesLabel(summary.actual_minutes)}</span>
                <span>見積 {minutesLabel(summary.estimated_minutes)}</span>
                <span className={summary.variance_minutes >= 0 ? "positive" : "negative"}>差分 {minutesLabel(summary.variance_minutes)}</span>
              </button>
            ))}
          </div>
          {selected && (
            <div className="dashboardDetail">
              <div className="detailHeader">
                <h3>{selected.assignee.name} 詳細</h3>
                <span>効率: {selected.efficiency_rate === null ? "-" : `${selected.efficiency_rate}%`}</span>
              </div>
              <div className="processBreakdown">
                {selected.processes.length === 0 && <p>この期間の作業実績はありません。</p>}
                {selected.processes.map((process) => (
                  <div key={process.name}>
                    <strong>{process.name}</strong>
                    <span>{process.work_count}件</span>
                    <span>実績 {minutesLabel(process.actual_minutes)}</span>
                    <span>見積 {minutesLabel(process.estimated_minutes)}</span>
                  </div>
                ))}
              </div>
              <div className="tableScroll">
                <table>
                  <thead>
                    <tr><th>日付</th><th>時刻</th><th>工程</th><th>図番</th><th>分類</th><th>数量</th><th>実績</th><th>見積</th><th>差分</th></tr>
                  </thead>
                  <tbody>
                    {selected.logs.map((log) => (
                      <tr key={log.id}>
                        <td>{log.work_date}</td>
                        <td>{log.start_time ?? "-"}〜{log.end_time ?? "-"}</td>
                        <td>{log.process_name}</td>
                        <td>{log.drawing_no}</td>
                        <td>{log.work_type}</td>
                        <td>{log.completed_qty_delta}</td>
                        <td>{minutesLabel(log.duration_minutes)}</td>
                        <td>{minutesLabel(log.estimated_minutes)}</td>
                        <td>{minutesLabel(log.estimated_minutes - log.duration_minutes)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
