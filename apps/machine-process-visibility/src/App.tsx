import { useEffect, useMemo, useState } from "react";
import { clearToken, getToken, request, setToken } from "./api";
import { CardModal } from "./components/CardModal";
import type { AuthUser, Card, CardDraft, LoginResponse, Meta, Process, ProcessSortMode, View } from "./types";
import { emptyCard, isRework, PROCESS_VIEW_NAMES, toPayload } from "./utils/card";
import { AssigneeView } from "./views/AssigneeView";
import { AdminView } from "./views/AdminView";
import { BoardView } from "./views/BoardView";
import { CalendarView } from "./views/CalendarView";
import { DashboardView } from "./views/DashboardView";
import { LoginView } from "./views/LoginView";
import { PasswordChangeView } from "./views/PasswordChangeView";
import { ProcessView } from "./views/ProcessView";

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
    setToken(result.token);
    setUser(result.user);
    if (!result.user.password_must_change) {
      await load();
    }
  }

  async function handleLogout() {
    await request("/auth/logout", { method: "POST" }).catch(() => undefined);
    clearToken();
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
    const movedCard = {
      ...card,
      current_process_id: process.id,
      process,
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
      const token = getToken();
      if (!token) {
        setBooting(false);
        return;
      }
      try {
        const current = await request<AuthUser>("/auth/me");
        setUser(current);
        await load();
      } catch {
        clearToken();
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

  if (user.password_must_change) {
    return (
      <PasswordChangeView
        user={user}
        onChanged={(nextUser) => {
          setUser(nextUser);
          load().catch((err) => setError(err.message));
        }}
        onLogout={handleLogout}
      />
    );
  }

  const isAdmin = user.role === "admin";

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
            ...(isAdmin ? [["dashboard", "ダッシュボード"]] : []),
            ...(isAdmin ? [["admin", "管理"]] : []),
          ].map(([key, label]) => (
            <button key={key} className={view === key ? "active" : ""} onClick={() => setView(key as View)}>
              {label}
            </button>
          ))}
          <span className="userBadge">{user.display_name} / {isAdmin ? "admin" : "operator"}</span>
          <button onClick={handleLogout}>ログアウト</button>
        </nav>
      </header>

      <main>
        {error && <div className="error">{error}</div>}
        <div className="toolbar">
          {isAdmin && <button onClick={() => setSelectedCard(emptyCard(meta))}>カード作成</button>}
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
        {view === "board" && <BoardView cards={visibleCards} processes={meta.processes} onOpen={openCard} onMove={moveCard} canMove={isAdmin} />}
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
        {view === "dashboard" && isAdmin && <DashboardView />}
        {view === "admin" && isAdmin && <AdminView meta={meta} onMetaChanged={load} />}
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
