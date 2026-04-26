import { DragEvent, FormEvent, useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8000/api";
const PROCESS_VIEW_NAMES = ["内面研磨", "刃物研磨", "機械加工", "板金加工", "手加工"];

type Process = { id: number; name: string; sort_order: number; active: number };
type Assignee = { id: number; name: string; color: string; active: number };
type Tag = { id: number; name: string; color: string };
type Card = {
  id: number;
  order_no: string;
  item_type: string;
  drawing_no: string;
  item_name: string;
  remarks: string;
  total_qty: number;
  completed_qty: number;
  current_process_id: number;
  status: "未着手" | "作業中" | "完了";
  assignee_id: number | null;
  planned_work_date: string | null;
  due_date: string | null;
  description: string;
  progress_rate: number;
  assignee: Assignee | null;
  process: Process;
  tags: Tag[];
  comments?: Comment[];
  work_logs?: WorkLog[];
};
type Comment = {
  id: number;
  comment_type: string;
  body: string;
  user_name?: string;
  created_at: string;
};
type WorkLog = {
  id: number;
  work_date: string;
  completed_qty_delta: number;
  work_hours: number;
  assignee_name?: string;
  comment_type?: string;
  comment_body?: string;
  created_at: string;
};
type ReportRow = {
  work_date: string;
  assignee_name: string;
  process_name: string;
  order_no: string;
  item_type: string;
  drawing_no: string;
  item_name: string;
  remarks: string;
  completed_qty_delta: number;
  work_hours: number;
  comment_type: string;
  comment: string;
  finding: string;
};
type Meta = { processes: Process[]; assignees: Assignee[]; tags: Tag[]; comment_types: string[] };
type View = "board" | "process" | "assignee" | "calendar" | "report";
type ProcessSortMode = "due" | "assignee";
type AuthUser = {
  id: number;
  username: string;
  display_name: string;
  assignee_id: number | null;
  assignee: Assignee | null;
  role: string;
};
type LoginResponse = { token: string; user: AuthUser };
type WorkFormState = {
  work_date: string;
  completed_qty_delta: number;
  work_hours: number;
  assignee_id: number | null;
  comment_type: string;
  comment: string;
};
type CardDraft = Omit<Card, "id" | "progress_rate" | "assignee" | "process" | "tags" | "comments" | "work_logs"> & {
  id?: number;
  progress_rate?: number;
  assignee?: Assignee | null;
  process?: Process;
  tags?: Tag[];
  comments?: Comment[];
  work_logs?: WorkLog[];
  tag_ids?: number[];
};

const emptyCard = (meta: Meta): CardDraft => ({
  order_no: "",
  item_type: "",
  drawing_no: "",
  item_name: "",
  remarks: "",
  total_qty: 1,
  completed_qty: 0,
  current_process_id: meta.processes[0]?.id ?? 1,
  status: "未着手",
  assignee_id: meta.assignees[0]?.id ?? null,
  planned_work_date: "",
  due_date: "",
  description: "【状態】\n\n【注意】\n\n【次工程】\n",
  tag_ids: [],
});

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("machine_poc_token");
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 401) {
    localStorage.removeItem("machine_poc_token");
  }
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "APIエラー" }));
    throw new Error(error.detail ?? "APIエラー");
  }
  return res.json();
}

function labelStyle(color?: string) {
  return { backgroundColor: color ?? "#64748b" };
}

function pad2(value: number | string) {
  return String(value).padStart(2, "0");
}

function localDateString(date = new Date()) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function monthKey(date: Date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}`;
}

function normalizeDateInput(raw: string) {
  const value = raw.trim();
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const separated = value.match(/^(\d{1,4})[/-](\d{1,2})(?:[/-](\d{1,2}))?$/);
  if (separated) {
    if (separated[3]) {
      const yyyy = separated[1].length === 4 ? Number(separated[1]) : year;
      return `${yyyy}-${pad2(separated[2])}-${pad2(separated[3])}`;
    }
    return `${year}-${pad2(separated[1])}-${pad2(separated[2])}`;
  }

  if (/^\d{8}$/.test(value)) {
    return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
  }
  if (/^\d{4}$/.test(value)) {
    return `${year}-${value.slice(0, 2)}-${value.slice(2, 4)}`;
  }
  if (/^\d{1,2}$/.test(value)) {
    return `${year}-${pad2(month)}-${pad2(value)}`;
  }
  return value;
}

function isDatePickerValue(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : "";
}

function DateField({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}) {
  const control = (
    <div className="dateField">
      <input
        type="text"
        inputMode="numeric"
        placeholder="例: 0425 / 4/25"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onBlur={(event) => onChange(normalizeDateInput(event.target.value))}
      />
      <input
        className="datePicker"
        type="date"
        value={isDatePickerValue(value)}
        onChange={(event) => onChange(event.target.value)}
        aria-label={`${label ?? "日付"}をカレンダーから選択`}
      />
    </div>
  );
  return label ? <label>{label}{control}</label> : control;
}

function percent(card: Card) {
  return `${card.completed_qty}/${card.total_qty} (${card.progress_rate}%)`;
}

function isRework(card: Card) {
  return card.tags.some((tag) => tag.name === "追加工");
}

function toPayload(card: Card | CardDraft, tagIds?: number[]) {
  return {
    order_no: card.order_no ?? "",
    item_type: card.item_type ?? "",
    drawing_no: card.drawing_no,
    item_name: card.item_name,
    remarks: card.remarks ?? "",
    total_qty: Number(card.total_qty),
    completed_qty: Number(card.completed_qty),
    current_process_id: Number(card.current_process_id),
    status: card.status,
    assignee_id: card.assignee_id ? Number(card.assignee_id) : null,
    planned_work_date: card.planned_work_date || null,
    due_date: card.due_date || null,
    description: card.description,
    tag_ids: tagIds ?? card.tags?.map((tag) => tag.id) ?? ("tag_ids" in card ? card.tag_ids ?? [] : []),
  };
}

export function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [booting, setBooting] = useState(true);
  const [meta, setMeta] = useState<Meta>({ processes: [], assignees: [], tags: [], comment_types: [] });
  const [cards, setCards] = useState<Card[]>([]);
  const [view, setView] = useState<View>("board");
  const [selectedCard, setSelectedCard] = useState<Card | CardDraft | null>(null);
  const [error, setError] = useState("");
  const [reworkOnly, setReworkOnly] = useState(false);
  const [mineOnly, setMineOnly] = useState(false);
  const [selectedProcessId, setSelectedProcessId] = useState<number | null>(null);
  const [processSortMode, setProcessSortMode] = useState<ProcessSortMode>("assignee");

  async function load() {
    setError("");
    const [nextMeta, nextCards] = await Promise.all([request<Meta>("/meta"), request<Card[]>("/cards")]);
    setMeta(nextMeta);
    setCards(nextCards);
  }

  async function handleLogin(username: string, password: string) {
    setError("");
    const result = await request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    localStorage.setItem("machine_poc_token", result.token);
    setUser(result.user);
    await load();
  }

  async function handleLogout() {
    await request("/auth/logout", { method: "POST" }).catch(() => undefined);
    localStorage.removeItem("machine_poc_token");
    setUser(null);
    setCards([]);
    setSelectedCard(null);
  }

  async function openCard(id: number) {
    setSelectedCard(await request<Card>(`/cards/${id}`));
  }

  async function refreshCard(id: number) {
    const card = await request<Card>(`/cards/${id}`);
    setSelectedCard(card);
    await load();
  }

  async function moveCard(card: Card, process: Process) {
    if (card.current_process_id === process.id) return;
    const nextStatus: Card["status"] = process.name === "完了" ? "完了" : process.name === "未振り分け" ? "未着手" : "作業中";
    const movedCard = {
      ...card,
      current_process_id: process.id,
      process,
      status: nextStatus,
    };
    setCards((current) => current.map((item) => (item.id === card.id ? movedCard : item)));
    setError("");
    try {
      await request<Card>(`/cards/${card.id}`, {
        method: "PUT",
        body: JSON.stringify(toPayload(movedCard)),
      });
      await load();
    } catch (err) {
      setError((err as Error).message);
      await load();
    }
  }

  useEffect(() => {
    async function boot() {
      const token = localStorage.getItem("machine_poc_token");
      if (!token) {
        setBooting(false);
        return;
      }
      try {
        const current = await request<AuthUser>("/auth/me");
        setUser(current);
        await load();
      } catch {
        localStorage.removeItem("machine_poc_token");
      } finally {
        setBooting(false);
      }
    }
    boot();
  }, []);

  const visibleCards = useMemo(() => {
    let next = cards;
    if (reworkOnly) next = next.filter(isRework);
    if (mineOnly && user?.assignee_id) next = next.filter((card) => card.assignee_id === user.assignee_id);
    return next;
  }, [cards, reworkOnly, mineOnly, user?.assignee_id]);

  useEffect(() => {
    if (!selectedProcessId && meta.processes.length > 0) {
      const firstProcess = meta.processes.find((process) => PROCESS_VIEW_NAMES.includes(process.name)) ?? meta.processes[0];
      setSelectedProcessId(firstProcess.id);
    }
  }, [meta.processes, selectedProcessId]);

  if (booting) {
    return <div className="boot">読み込み中...</div>;
  }

  if (!user) {
    return <LoginView error={error} onLogin={(username, password) => handleLogin(username, password).catch((err) => setError(err.message))} />;
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>機械課 工程見える化</h1>
          <p>図番単位で工程、担当、進捗、追加工を管理</p>
        </div>
        <nav>
          {[
            ["board", "全体ボード"],
            ["process", "島別"],
            ["assignee", "担当者別"],
            ["calendar", "カレンダー"],
            ["report", "日報"],
          ].map(([key, label]) => (
            <button key={key} className={view === key ? "active" : ""} onClick={() => setView(key as View)}>
              {label}
            </button>
          ))}
          <span className="userBadge">{user.display_name}</span>
          <button onClick={handleLogout}>ログアウト</button>
        </nav>
      </header>

      <main>
        {error && <div className="error">{error}</div>}
        <div className="toolbar">
          <button onClick={() => setSelectedCard(emptyCard(meta))}>カード作成</button>
          <label className="check">
            <input type="checkbox" checked={reworkOnly} onChange={(event) => setReworkOnly(event.target.checked)} />
            追加工のみ
          </label>
          {user.assignee_id && (
            <label className="check">
              <input type="checkbox" checked={mineOnly} onChange={(event) => setMineOnly(event.target.checked)} />
              自分の担当のみ
            </label>
          )}
        </div>
        {view === "board" && <Board cards={visibleCards} processes={meta.processes} onOpen={openCard} onMove={moveCard} />}
        {view === "process" && (
          <ProcessView
            cards={visibleCards}
            processes={meta.processes}
            assignees={meta.assignees}
            selectedProcessId={selectedProcessId}
            sortMode={processSortMode}
            onSelectProcess={setSelectedProcessId}
            onSortModeChange={setProcessSortMode}
            onOpen={openCard}
          />
        )}
        {view === "assignee" && <AssigneeView cards={visibleCards} assignees={meta.assignees} onOpen={openCard} />}
        {view === "calendar" && <CalendarView cards={visibleCards} onOpen={openCard} />}
        {view === "report" && <ReportView meta={meta} />}
      </main>

      {selectedCard && (
        <CardModal
          card={selectedCard}
          meta={meta}
          currentUser={user}
          onClose={() => setSelectedCard(null)}
          onSaved={(id) => refreshCard(id).catch((err) => setError(err.message))}
        />
      )}
    </div>
  );
}

function LoginView({ error, onLogin }: { error: string; onLogin: (username: string, password: string) => void }) {
  const [username, setUsername] = useState("mitani");
  const [password, setPassword] = useState("password");

  function submit(event: FormEvent) {
    event.preventDefault();
    onLogin(username, password);
  }

  return (
    <div className="loginPage">
      <form className="loginBox" onSubmit={submit}>
        <h1>機械課 工程見える化</h1>
        <label>
          ユーザー名
          <input value={username} onChange={(event) => setUsername(event.target.value)} autoFocus />
        </label>
        <label>
          パスワード
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="primary" type="submit">ログイン</button>
        <p>PoC初期ユーザー: mitani / password</p>
      </form>
    </div>
  );
}

function Board({
  cards,
  processes,
  onOpen,
  onMove,
}: {
  cards: Card[];
  processes: Process[];
  onOpen: (id: number) => void;
  onMove: (card: Card, process: Process) => void;
}) {
  const [draggingCardId, setDraggingCardId] = useState<number | null>(null);
  const [dropProcessId, setDropProcessId] = useState<number | null>(null);

  function handleDrop(event: DragEvent<HTMLDivElement>, process: Process) {
    event.preventDefault();
    setDropProcessId(null);
    const cardId = Number(event.dataTransfer.getData("text/plain"));
    const card = cards.find((item) => item.id === cardId);
    if (card) onMove(card, process);
  }

  return (
    <section className="board">
      {processes.map((process) => (
        (() => {
          const processCards = cards.filter((card) => card.current_process_id === process.id);
          return (
        <div
          className={`column ${dropProcessId === process.id ? "dropTarget" : ""}`}
          key={process.id}
          onDragOver={(event) => {
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
                draggable
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
        })()
      ))}
    </section>
  );
}

function ProcessView({
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

function AssigneeView({ cards, assignees, onOpen }: { cards: Card[]; assignees: Assignee[]; onOpen: (id: number) => void }) {
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

function CalendarView({ cards, onOpen }: { cards: Card[]; onOpen: (id: number) => void }) {
  const [displayMonth, setDisplayMonth] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 1);
  });
  const todayKey = localDateString();
  const currentMonthKey = monthKey(displayMonth);
  const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
  const entriesByDay = new Map<string, { card: Card; kind: "予定" | "納期" }[]>();

  cards.forEach((card) => {
    [
      { day: card.planned_work_date, kind: "予定" as const },
      { day: card.due_date, kind: "納期" as const },
    ].forEach(({ day, kind }) => {
      if (!day || !day.startsWith(currentMonthKey)) return;
      entriesByDay.set(day, [...(entriesByDay.get(day) ?? []), { card, kind }]);
    });
  });

  const firstDay = new Date(displayMonth.getFullYear(), displayMonth.getMonth(), 1);
  const daysInMonth = new Date(displayMonth.getFullYear(), displayMonth.getMonth() + 1, 0).getDate();
  const leadingBlankCount = firstDay.getDay();
  const dayCells: (string | null)[] = [
    ...Array.from({ length: leadingBlankCount }, () => null),
    ...Array.from({ length: daysInMonth }, (_, index) => `${currentMonthKey}-${pad2(index + 1)}`),
  ];
  while (dayCells.length % 7 !== 0) {
    dayCells.push(null);
  }

  function moveMonth(delta: number) {
    setDisplayMonth((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1));
  }

  return (
    <section className="panel">
      <div className="calendarToolbar">
        <button onClick={() => moveMonth(-1)}>前月</button>
        <h2>{displayMonth.getFullYear()}年 {displayMonth.getMonth() + 1}月</h2>
        <button onClick={() => moveMonth(1)}>翌月</button>
        <button onClick={() => setDisplayMonth(new Date(new Date().getFullYear(), new Date().getMonth(), 1))}>今月</button>
      </div>
      <div className="monthCalendar">
        {weekdays.map((weekday) => (
          <div className="weekday" key={weekday}>{weekday}</div>
        ))}
        {dayCells.map((day, index) => (
          <div className={`dayCell ${day ? "" : "empty"} ${day === todayKey ? "today" : ""}`} key={day ?? `blank-${index}`}>
            {day && (
              <>
                <div className="dayNumber">{Number(day.slice(-2))}</div>
                <div className="calendarItems">
                  {(entriesByDay.get(day) ?? []).map(({ card, kind }) => (
                    <button className={`calendarItem ${isRework(card) ? "rework" : ""}`} key={`${day}-${kind}-${card.id}`} onClick={() => onOpen(card.id)}>
                      <span>{card.drawing_no}</span>
                      <small>{kind} / {card.process.name}</small>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
      <div className="calendarEmptyNote">
        {dayCells.every((day) => !day || !entriesByDay.get(day)?.length) && "この月の予定・納期はありません"}
      </div>
    </section>
  );
}

function ReportView({ meta }: { meta: Meta }) {
  const today = localDateString();
  const [workDate, setWorkDate] = useState(today);
  const [assigneeId, setAssigneeId] = useState("");
  const [processId, setProcessId] = useState("");
  const [rows, setRows] = useState<ReportRow[]>([]);
  const [error, setError] = useState("");

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
    const token = localStorage.getItem("machine_poc_token");
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
    anchor.download = "daily_report.csv";
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
      <div className="tableScroll">
        <table className="report">
          <thead>
            <tr>
              <th>日付</th>
              <th>担当者</th>
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

function CardTile({
  card,
  onOpen,
  compact = false,
  draggable = false,
  dragging = false,
  onDragStart,
  onDragEnd,
}: {
  card: Card;
  onOpen: (id: number) => void;
  compact?: boolean;
  draggable?: boolean;
  dragging?: boolean;
  onDragStart?: () => void;
  onDragEnd?: () => void;
}) {
  return (
    <button
      className={`card ${isRework(card) ? "rework" : ""} ${dragging ? "dragging" : ""}`}
      draggable={draggable}
      onClick={() => onOpen(card.id)}
      onDragStart={(event) => {
        if (!draggable) return;
        event.dataTransfer.setData("text/plain", String(card.id));
        event.dataTransfer.effectAllowed = "move";
        onDragStart?.();
      }}
      onDragEnd={onDragEnd}
    >
      {card.tags.length > 0 && (
        <div className="cardLabels">
          {card.tags.map((tag) => <span className="tagStrip" style={labelStyle(tag.color)} key={tag.id}>{tag.name}</span>)}
        </div>
      )}
      <div className="cardHead">
        <div>
          <strong>{card.drawing_no}</strong>
          <p>{card.item_name}</p>
        </div>
        <span>{card.status}</span>
      </div>
      {(card.order_no || card.item_type) && (
        <div className="subMeta">
          {card.order_no && <span>受注 {card.order_no}</span>}
          {card.item_type && <span>{card.item_type}</span>}
        </div>
      )}
      {card.remarks && <p className="remarksLine">{card.remarks}</p>}
      <div className="progress">
        <div style={{ width: `${card.progress_rate}%` }} />
      </div>
      <div className="cardFooter">
        {card.assignee ? (
          <span className="avatar" style={labelStyle(card.assignee.color)} title={card.assignee.name}>
            {card.assignee.name.slice(0, 1)}
          </span>
        ) : (
          <span className="avatar empty">?</span>
        )}
        <span>{percent(card)}</span>
      </div>
      <div className="metaLine">
        {!compact && <span>予定 {card.planned_work_date ?? "-"}</span>}
        <span>納期 {card.due_date ?? "-"}</span>
      </div>
    </button>
  );
}

function CardModal({
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
      await request(`/cards/${cardId}/work-results`, { method: "POST", body: JSON.stringify(work) });
      setWork({
        work_date: localDateString(),
        completed_qty_delta: 0,
        work_hours: 0,
        assignee_id: currentUser.assignee_id ?? draft.assignee_id ?? meta.assignees[0]?.id ?? null,
        comment_type: "作業",
        comment: "",
      });
      onSaved(cardId);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function update<K extends keyof CardDraft>(key: K, value: CardDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

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
          </div>
        )}
        <form className="detailGrid" onSubmit={save}>
          <label>受注番号<input value={draft.order_no ?? ""} placeholder="例: E-25086" pattern="[A-Z]-[0-9]{5}" onChange={(e) => update("order_no", e.target.value.toUpperCase())} /></label>
          <label>種別<input value={draft.item_type ?? ""} placeholder="例: 01" inputMode="numeric" pattern="[0-9]{2}" maxLength={2} onChange={(e) => update("item_type", e.target.value.replace(/\D/g, "").slice(0, 2))} /></label>
          <label>図番<input value={draft.drawing_no} onChange={(e) => update("drawing_no", e.target.value)} required /></label>
          <label>品名<input value={draft.item_name} onChange={(e) => update("item_name", e.target.value)} required /></label>
          <label>総数<input type="number" min="0" value={draft.total_qty} onChange={(e) => update("total_qty", Number(e.target.value))} /></label>
          <label>完了数<input type="number" min="0" value={draft.completed_qty} onChange={(e) => update("completed_qty", Number(e.target.value))} /></label>
          <label>進捗率<input value={`${draft.total_qty ? Math.round((draft.completed_qty / draft.total_qty) * 100) : 0}%`} readOnly /></label>
          <label>現在工程
            <select value={draft.current_process_id} onChange={(e) => update("current_process_id", Number(e.target.value))}>
              {meta.processes.map((process) => <option key={process.id} value={process.id}>{process.name}</option>)}
            </select>
          </label>
          <label>ステータス
            <select value={draft.status} onChange={(e) => update("status", e.target.value as Card["status"])}>
              <option>未着手</option><option>作業中</option><option>完了</option>
            </select>
          </label>
          <label>担当者
            <select value={draft.assignee_id ?? ""} onChange={(e) => update("assignee_id", e.target.value ? Number(e.target.value) : null)}>
              <option value="">未設定</option>
              {meta.assignees.map((assignee) => <option key={assignee.id} value={assignee.id}>{assignee.name}</option>)}
            </select>
          </label>
          <DateField label="作業予定日" value={draft.planned_work_date ?? ""} onChange={(value) => update("planned_work_date", value)} />
          <DateField label="納期" value={draft.due_date ?? ""} onChange={(value) => update("due_date", value)} />
          <fieldset className="tags">
            <legend>タグ</legend>
            {meta.tags.map((tag) => (
              <label key={tag.id} className="tagChoice">
                <input
                  type="checkbox"
                  checked={tagIds.includes(tag.id)}
                  onChange={(event) => {
                    setTagIds((current) => event.target.checked ? [...current, tag.id] : current.filter((id) => id !== tag.id));
                  }}
                />
                <span className="label" style={labelStyle(tag.color)}>{tag.name}</span>
              </label>
            ))}
          </fieldset>
          <label className="wide">備考<input value={draft.remarks ?? ""} onChange={(e) => update("remarks", e.target.value)} /></label>
          <label className="wide">説明欄<textarea rows={6} value={draft.description} onChange={(e) => update("description", e.target.value)} /></label>
          <button className="primary" type="submit">保存</button>
        </form>

        {!isNew && (
          <div className="modalSections">
            <form className="workForm" onSubmit={addWork}>
              <h3>作業実績を登録</h3>
              <DateField label="作業日" value={work.work_date} onChange={(value) => setWork({ ...work, work_date: value })} />
              <label>
                作業者
                <select value={work.assignee_id ?? ""} onChange={(e) => setWork({ ...work, assignee_id: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">未設定</option>
                  {meta.assignees.map((assignee) => <option key={assignee.id} value={assignee.id}>{assignee.name}</option>)}
                </select>
              </label>
              <input type="number" min="0" placeholder="今回完了数" value={work.completed_qty_delta} onChange={(e) => setWork({ ...work, completed_qty_delta: Number(e.target.value) })} />
              <input type="number" min="0" step="0.25" placeholder="作業時間" value={work.work_hours} onChange={(e) => setWork({ ...work, work_hours: Number(e.target.value) })} />
              <select value={work.comment_type} onChange={(e) => setWork({ ...work, comment_type: e.target.value })}>
                {meta.comment_types.map((type) => <option key={type}>{type}</option>)}
              </select>
              <input placeholder="コメント" value={work.comment} onChange={(e) => setWork({ ...work, comment: e.target.value })} />
              <button type="submit">登録</button>
            </form>

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
                  <thead><tr><th>日付</th><th>担当</th><th>完了数</th><th>時間</th><th>コメント</th></tr></thead>
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
