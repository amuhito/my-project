import { useEffect, useMemo, useState } from "react";
import {
  archiveCard,
  clearStoredAuthToken,
  createUser,
  createCard,
  fetchBoard,
  fetchCard,
  fetchCurrentUser,
  fetchUsers,
  getStoredAuthToken,
  login,
  moveCard,
  unarchiveCard,
} from "./api";
import { CardModal } from "./components/CardModal";
import type { AuthUser, BoardList, BoardResponse, CardDetail, CardSummary } from "./types";

type DragState = {
  cardId: number;
  sourceListId: number;
};

type ViewMode = "kanban" | "table";
type UrgencyFilter = "all" | "overdue" | "with-response-date";
type TableSortMode = "default" | "requested-due" | "response-due" | "order-no";

type ContextMenuState = {
  x: number;
  y: number;
  card: CardSummary;
};

const ARCHIVABLE_STATUS = "１次対応完了";

function todayText() {
  return new Date().toISOString().slice(0, 10);
}

function canArchiveCard(card: Pick<CardSummary, "archived" | "status" | "requested_due_date">) {
  if (card.archived) {
    return true;
  }

  return card.status === ARCHIVABLE_STATUS && !!card.requested_due_date && card.requested_due_date < todayText();
}

function countBusinessDaysSince(dateText: string) {
  const baseDate = new Date(`${dateText.slice(0, 10)}T00:00:00`);
  const today = new Date(`${todayText()}T00:00:00`);

  if (Number.isNaN(baseDate.getTime()) || baseDate >= today) {
    return 0;
  }

  let businessDays = 0;
  const current = new Date(baseDate);
  current.setDate(current.getDate() + 1);

  while (current < today) {
    const day = current.getDay();
    if (day !== 0 && day !== 6) {
      businessDays += 1;
    }
    current.setDate(current.getDate() + 1);
  }

  return businessDays;
}

function toAlertLevel(diffDays: number) {
  if (diffDays >= 2) {
    return 2;
  }
  if (diffDays >= 1) {
    return 1;
  }
  return 0;
}

function getAgedAlert(
  card: Pick<CardSummary, "archived" | "status" | "received_date" | "latest_activity_at">,
) {
  if (card.archived) {
    return null;
  }

  const activityLevel = card.latest_activity_at
    ? toAlertLevel(countBusinessDaysSince(card.latest_activity_at))
    : 0;
  const receivedLevel =
    card.status === "未対応" && card.received_date
      ? toAlertLevel(countBusinessDaysSince(card.received_date))
      : 0;

  if (receivedLevel >= activityLevel && receivedLevel > 0) {
    return {
      level: receivedLevel,
      label: receivedLevel >= 2 ? "未対応2営業日以上経過" : "未対応1営業日経過",
    };
  }

  if (activityLevel > 0) {
    return {
      level: activityLevel,
      label: activityLevel >= 2 ? "2営業日以上経過" : "1営業日経過",
    };
  }

  return null;
}

function isUnauthorizedError(error: unknown) {
  return error instanceof Error && error.message === "UNAUTHORIZED";
}

function App() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [board, setBoard] = useState<BoardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeCard, setActiveCard] = useState<CardDetail | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [error, setError] = useState("");
  const [newCardTitles, setNewCardTitles] = useState<Record<number, string>>({});
  const [creatingListId, setCreatingListId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("kanban");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [urgencyFilter, setUrgencyFilter] = useState<UrgencyFilter>("all");
  const [tableSort, setTableSort] = useState<TableSortMode>("default");
  const [showArchived, setShowArchived] = useState(false);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [managedUsers, setManagedUsers] = useState<AuthUser[]>([]);
  const [userManageLoading, setUserManageLoading] = useState(false);
  const [userManageError, setUserManageError] = useState("");

  useEffect(() => {
    void restoreSession();
  }, []);

  useEffect(() => {
    if (!currentUser) {
      setBoard(null);
      setLoading(false);
      return;
    }
    void loadBoard();
  }, [showArchived, currentUser]);

  useEffect(() => {
    const closeMenu = () => setContextMenu(null);
    window.addEventListener("click", closeMenu);
    return () => window.removeEventListener("click", closeMenu);
  }, []);

  const statuses = useMemo(() => board?.lists.map((list) => list.title) ?? [], [board]);

  const cardLookup = useMemo(() => {
    const map = new Map<number, { listId: number }>();
    board?.lists.forEach((list) => {
      list.cards.forEach((card) => {
        map.set(card.id, { listId: list.id });
      });
    });
    return map;
  }, [board]);

  const filteredLists = useMemo(() => {
    if (!board) {
      return [];
    }

    const today = new Date().toISOString().slice(0, 10);
    const normalizedQuery = searchQuery.trim().toLowerCase();
    return board.lists.map((list) => ({
      ...list,
      cards: list.cards.filter((card) => {
        if (statusFilter !== "all" && card.status !== statusFilter) {
          return false;
        }

        if (urgencyFilter === "overdue") {
          if (!card.response_due_date || card.response_due_date >= today) {
            return false;
          }
        }

        if (urgencyFilter === "with-response-date" && !card.response_due_date) {
          return false;
        }

        if (!normalizedQuery) {
          return true;
        }

        const joinedText = [
          card.project_no,
          card.customer_name,
          card.assignee_name,
          card.notes,
          card.title,
        ]
          .join(" ")
          .toLowerCase();

        return joinedText.includes(normalizedQuery);
      }),
    }));
  }, [board, searchQuery, statusFilter, urgencyFilter]);

  const flatCards = useMemo(() => {
    const cards = filteredLists.flatMap((list) =>
      list.cards.map((card, index) => ({
        ...card,
        listId: list.id,
        listTitle: list.title,
        originalIndex: index,
        listPosition: list.position,
      })),
    );

    if (tableSort === "default") {
      return cards;
    }

    const compareDate = (left: string | null, right: string | null) => {
      if (left && right) {
        return left.localeCompare(right);
      }
      if (left) {
        return -1;
      }
      if (right) {
        return 1;
      }
      return 0;
    };

    const compareFallback = (
      left: { listPosition: number; originalIndex: number },
      right: { listPosition: number; originalIndex: number },
    ) => {
      if (left.listPosition !== right.listPosition) {
        return left.listPosition - right.listPosition;
      }
      return left.originalIndex - right.originalIndex;
    };

    return [...cards].sort((left, right) => {
      if (tableSort === "requested-due") {
        const result = compareDate(left.requested_due_date, right.requested_due_date);
        return result !== 0 ? result : compareFallback(left, right);
      }

      if (tableSort === "response-due") {
        const result = compareDate(left.response_due_date, right.response_due_date);
        return result !== 0 ? result : compareFallback(left, right);
      }

      const orderResult = (left.project_no || "").localeCompare(
        right.project_no || "",
        "ja",
        { numeric: true },
      );
      return orderResult !== 0 ? orderResult : compareFallback(left, right);
    });
  }, [filteredLists, tableSort]);

  const loadBoard = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await fetchBoard(showArchived);
      setBoard(data);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleLogout();
        return;
      }
      setError("ボードの取得に失敗しました。バックエンドが起動しているか確認してください。");
    } finally {
      setLoading(false);
    }
  };

  const openCard = async (cardId: number) => {
    try {
      const card = await fetchCard(cardId);
      setActiveCard(card);
      setModalOpen(true);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleLogout();
        return;
      }
      setError("カード詳細の取得に失敗しました。");
    }
  };

  const handleDrop = async (destinationListId: number, destinationIndex: number) => {
    if (!dragState) {
      return;
    }

    try {
      const updatedBoard = await moveCard({
        card_id: dragState.cardId,
        source_list_id: dragState.sourceListId,
        destination_list_id: destinationListId,
        destination_index: destinationIndex,
      });
      setBoard(updatedBoard);
      if (activeCard && activeCard.id === dragState.cardId) {
        const updatedCard = await fetchCard(activeCard.id);
        setActiveCard(updatedCard);
      }
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleLogout();
        return;
      }
      setError("カード移動に失敗しました。");
    } finally {
      setDragState(null);
    }
  };

  const handleCardSaved = async (updatedCard: CardDetail) => {
    try {
      setActiveCard(updatedCard);
      const updatedBoard = await fetchBoard(showArchived);
      setBoard(updatedBoard);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleLogout();
        return;
      }
      setError("ボードの再取得に失敗しました。");
    }
  };

  const handleArchiveToggle = async (cardId: number, archived: boolean) => {
    const targetCard =
      board?.lists.flatMap((list) => list.cards).find((card) => card.id === cardId) ??
      (activeCard && activeCard.id === cardId ? activeCard : null);

    if (!archived && targetCard && !canArchiveCard(targetCard)) {
      setError("アーカイブできるのは「１次対応完了」かつ希望納期を過ぎた案件だけです。");
      setContextMenu(null);
      return;
    }

    try {
      setError("");
      const updatedCard = archived ? await unarchiveCard(cardId) : await archiveCard(cardId);
      const updatedBoard = await fetchBoard(showArchived);
      setBoard(updatedBoard);
      setContextMenu(null);
      if (activeCard?.id === cardId) {
        if (!updatedCard.archived || showArchived) {
          setActiveCard(updatedCard);
        } else {
          setActiveCard(null);
          setModalOpen(false);
        }
      }
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleLogout();
        return;
      }
      setError("アーカイブ操作に失敗しました。");
    }
  };

  const handleNewCardTitleChange = (listId: number, title: string) => {
    setNewCardTitles((current) => ({
      ...current,
      [listId]: title,
    }));
  };

  const handleCreateCard = async (listId: number) => {
    const orderNo = newCardTitles[listId]?.trim() ?? "";
    if (!orderNo) {
      setError("受注番号を入力してください。");
      return;
    }

    try {
      setCreatingListId(listId);
      setError("");
      const createdCard = await createCard(listId, {
        title: "",
        project_no: orderNo,
      });
      const updatedBoard = await fetchBoard(showArchived);
      setBoard(updatedBoard);
      setNewCardTitles((current) => ({
        ...current,
        [listId]: "",
      }));
      setActiveCard(createdCard);
      setModalOpen(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "カードの追加に失敗しました。";
      if (isUnauthorizedError(error)) {
        handleLogout();
        return;
      }
      setError(message);
    } finally {
      setCreatingListId(null);
    }
  };

  const restoreSession = async () => {
    const token = getStoredAuthToken();
    if (!token) {
      setAuthLoading(false);
      return;
    }

    try {
      const me = await fetchCurrentUser();
      setCurrentUser(me);
      setError("");
    } catch {
      clearStoredAuthToken();
      setCurrentUser(null);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogin = async (username: string, password: string) => {
    const user = await login(username, password);
    setCurrentUser(user);
    setError("");
  };

  const handleLogout = () => {
    clearStoredAuthToken();
    setCurrentUser(null);
    setActiveCard(null);
    setModalOpen(false);
    setBoard(null);
    setError("");
  };

  const loadManagedUsers = async () => {
    try {
      setUserManageLoading(true);
      setUserManageError("");
      const users = await fetchUsers();
      setManagedUsers(users);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        handleLogout();
        return;
      }
      setUserManageError(error instanceof Error ? error.message : "ユーザー一覧の取得に失敗しました。");
    } finally {
      setUserManageLoading(false);
    }
  };

  const openUserManagement = async () => {
    setUserModalOpen(true);
    await loadManagedUsers();
  };

  const handleCreateManagedUser = async (payload: {
    username: string;
    display_name: string;
    password: string;
  }) => {
    await createUser(payload);
    await loadManagedUsers();
  };

  if (authLoading) {
    return <div className="screen-center">認証情報を確認中...</div>;
  }

  if (!currentUser) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  if (loading) {
    return <div className="screen-center">読み込み中...</div>;
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <div className="hero-badge">納期確認 POC</div>
          <h1>{board?.title ?? "納期確認ボード"}</h1>
          <p>案件ごとの確認状況を、カンバンとテーブルの両方で追えるローカルアプリです。</p>
        </div>
        <div className="hero-actions">
          <div className="login-user-chip">{currentUser.display_name}</div>
          {currentUser.username === "admin" ? (
            <button className="secondary-button" onClick={() => void openUserManagement()} type="button">
              ユーザー管理
            </button>
          ) : null}
          <button className="secondary-button" onClick={() => void loadBoard()} type="button">
            再読み込み
          </button>
          <button className="ghost-button" onClick={handleLogout} type="button">
            ログアウト
          </button>
        </div>
      </header>

      <section className="toolbar">
        <div className="toolbar-group">
          <button
            className={viewMode === "kanban" ? "primary-button" : "ghost-button"}
            onClick={() => setViewMode("kanban")}
            type="button"
          >
            カンバン
          </button>
          <button
            className={viewMode === "table" ? "primary-button" : "ghost-button"}
            onClick={() => setViewMode("table")}
            type="button"
          >
            テーブル
          </button>
        </div>
        <div className="toolbar-filters">
          <label className="search-box">
            <span className="search-label">検索</span>
            <input
              className="toolbar-input"
              placeholder="受注番号、ユーザー様、確認先、備考で検索"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </label>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">全ステータス</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          <select
            value={urgencyFilter}
            onChange={(event) => setUrgencyFilter(event.target.value as UrgencyFilter)}
          >
            <option value="all">すべて</option>
            <option value="with-response-date">回答納期あり</option>
            <option value="overdue">回答納期切れ</option>
          </select>
          <select
            value={tableSort}
            onChange={(event) => setTableSort(event.target.value as TableSortMode)}
          >
            <option value="default">並び: 既定順</option>
            <option value="requested-due">並び: 希望納期順</option>
            <option value="response-due">並び: 回答納期順</option>
            <option value="order-no">並び: 受注番号順</option>
          </select>
          <button
            className={showArchived ? "primary-button" : "ghost-button"}
            onClick={() => setShowArchived((current) => !current)}
            type="button"
          >
            {showArchived ? "アーカイブ表示中" : "アーカイブを表示"}
          </button>
        </div>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      {viewMode === "kanban" ? (
        <main className="board">
          {filteredLists.map((list) => (
            <KanbanColumn
              key={list.id}
              list={list}
              lookup={cardLookup}
              creatingListId={creatingListId}
              newCardTitle={newCardTitles[list.id] ?? ""}
              onChangeNewTitle={handleNewCardTitleChange}
              onCreateCard={handleCreateCard}
              onDrop={handleDrop}
              onOpenCard={openCard}
              onStartDrag={setDragState}
              onOpenContextMenu={setContextMenu}
            />
          ))}
        </main>
      ) : (
        <section className="table-panel">
          <div className="table-scroll">
            <table className="case-table">
              <thead>
                <tr>
                  <th>日付</th>
                  <th>受注番号</th>
                  <th>ユーザー様</th>
                  <th>ステータス</th>
                  <th>希望納期</th>
                  <th>確認先</th>
                  <th>回答納期</th>
                  <th>最短◎発送日</th>
                  <th>備考（理由）</th>
                </tr>
              </thead>
              <tbody>
                {flatCards.map((card) => (
                  <tr key={card.id} onClick={() => void openCard(card.id)}>
                    <td>{card.received_date ?? "-"}</td>
                    <td>{card.project_no || "-"}</td>
                    <td>{card.customer_name || card.title}</td>
                    <td>
                      {card.archived
                        ? "アーカイブ済み"
                        : canArchiveCard(card)
                          ? `${card.status}（アーカイブ可能）`
                          : card.status}
                    </td>
                    <td>{card.requested_due_date ?? "-"}</td>
                    <td>{card.assignee_name || "-"}</td>
                    <td>{card.response_due_date ?? "-"}</td>
                    <td>{card.earliest_ship_date ?? "-"}</td>
                    <td>{card.notes || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {contextMenu ? (
        <div
          className="context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(event) => event.stopPropagation()}
        >
          <button
            className="context-menu-item"
            onClick={() => void openCard(contextMenu.card.id)}
            type="button"
          >
            カードを開く
          </button>
          <button
            className="context-menu-item danger"
            disabled={!canArchiveCard(contextMenu.card)}
            onClick={() => void handleArchiveToggle(contextMenu.card.id, contextMenu.card.archived)}
            type="button"
          >
            {contextMenu.card.archived ? "アーカイブ解除" : "アーカイブ"}
          </button>
        </div>
      ) : null}

      <UserManagementModal
        open={userModalOpen}
        users={managedUsers}
        loading={userManageLoading}
        error={userManageError}
        onClose={() => setUserModalOpen(false)}
        onReload={() => void loadManagedUsers()}
        onCreateUser={(payload) => handleCreateManagedUser(payload)}
      />

      <CardModal
        card={activeCard}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSaved={(updatedCard) => void handleCardSaved(updatedCard)}
        onArchiveToggle={(cardId, archived) => void handleArchiveToggle(cardId, archived)}
        statuses={statuses}
      />
    </div>
  );
}

type LoginScreenProps = {
  onLogin: (username: string, password: string) => Promise<void>;
};

function LoginScreen({ onLogin }: LoginScreenProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!username.trim() || !password) {
      setError("ユーザー名とパスワードを入力してください。");
      return;
    }

    try {
      setLoading(true);
      setError("");
      await onLogin(username.trim(), password);
    } catch {
      setError("ログインに失敗しました。ユーザー名またはパスワードを確認してください。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1>納期確認カンバン</h1>
        <p>複数人での操作履歴を残すため、ログインしてください。</p>
        {error ? <div className="error-banner">{error}</div> : null}
        <label className="field">
          <span>ユーザー名</span>
          <input value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label className="field">
          <span>パスワード</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                void handleSubmit();
              }
            }}
          />
        </label>
        <button className="primary-button auth-submit" disabled={loading} onClick={() => void handleSubmit()} type="button">
          {loading ? "ログイン中..." : "ログイン"}
        </button>
      </div>
    </div>
  );
}

type UserManagementModalProps = {
  open: boolean;
  users: AuthUser[];
  loading: boolean;
  error: string;
  onClose: () => void;
  onReload: () => void;
  onCreateUser: (payload: { username: string; display_name: string; password: string }) => Promise<void>;
};

function UserManagementModal({
  open,
  users,
  loading,
  error,
  onClose,
  onReload,
  onCreateUser,
}: UserManagementModalProps) {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  if (!open) {
    return null;
  }

  const handleSubmit = async () => {
    if (!username.trim() || !displayName.trim() || !password) {
      setFormError("ユーザー名・表示名・パスワードを入力してください。");
      return;
    }

    try {
      setSaving(true);
      setFormError("");
      await onCreateUser({
        username: username.trim(),
        display_name: displayName.trim(),
        password,
      });
      setUsername("");
      setDisplayName("");
      setPassword("");
    } catch (submitError) {
      setFormError(
        submitError instanceof Error ? submitError.message : "ユーザー作成に失敗しました。",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="user-modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h2>ユーザー管理</h2>
          <div className="hero-actions">
            <button className="secondary-button" onClick={onReload} type="button">
              再取得
            </button>
            <button className="ghost-button" onClick={onClose} type="button">
              閉じる
            </button>
          </div>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}
        {formError ? <div className="error-banner">{formError}</div> : null}

        <div className="user-list-wrap">
          {loading ? (
            <div className="panel-muted">読み込み中...</div>
          ) : (
            <table className="user-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>ユーザー名</th>
                  <th>表示名</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.username}</td>
                    <td>{user.display_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <section className="panel">
          <h3>ユーザー追加</h3>
          <div className="row-fields row-fields-3">
            <label className="field">
              <span>ユーザー名</span>
              <input value={username} onChange={(event) => setUsername(event.target.value)} />
            </label>
            <label className="field">
              <span>表示名</span>
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
            </label>
            <label className="field">
              <span>パスワード</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    void handleSubmit();
                  }
                }}
              />
            </label>
          </div>
          <div className="modal-footer">
            <button className="primary-button" disabled={saving} onClick={() => void handleSubmit()} type="button">
              {saving ? "作成中..." : "作成"}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}

type KanbanColumnProps = {
  list: BoardList;
  lookup: Map<number, { listId: number }>;
  creatingListId: number | null;
  newCardTitle: string;
  onChangeNewTitle: (listId: number, title: string) => void;
  onCreateCard: (listId: number) => Promise<void>;
  onDrop: (destinationListId: number, destinationIndex: number) => Promise<void>;
  onOpenCard: (cardId: number) => Promise<void>;
  onStartDrag: (state: DragState) => void;
  onOpenContextMenu: (menu: ContextMenuState | null) => void;
};

function KanbanColumn({
  list,
  lookup,
  creatingListId,
  newCardTitle,
  onChangeNewTitle,
  onCreateCard,
  onDrop,
  onOpenCard,
  onStartDrag,
  onOpenContextMenu,
}: KanbanColumnProps) {
  return (
    <section
      className="list-column"
      onDragOver={(event) => event.preventDefault()}
      onDrop={() => void onDrop(list.id, list.cards.length)}
    >
      <div className="list-header">
        <h2>{list.title}</h2>
        <span>{list.cards.length} 件</span>
      </div>

      <div className="card-list">
        {list.cards.map((card, index) => (
          <article
            className={`card-tile${card.archived ? " card-tile-archived" : ""}${
              getAgedAlert(card)?.level === 1 ? " card-tile-alert" : ""
            }${
              (getAgedAlert(card)?.level ?? 0) >= 2 ? " card-tile-alert-strong" : ""
            }`}
            draggable={!card.archived}
            key={card.id}
            onClick={() => void onOpenCard(card.id)}
            onContextMenu={(event) => {
              event.preventDefault();
              onOpenContextMenu({
                x: event.clientX,
                y: event.clientY,
                card,
              });
            }}
            onDragStart={() =>
              onStartDrag({
                cardId: card.id,
                sourceListId: lookup.get(card.id)?.listId ?? list.id,
              })
            }
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              event.stopPropagation();
              void onDrop(list.id, index);
            }}
          >
            <div className="card-topline">
              <span className="card-order-no">{card.project_no || "受注番号未設定"}</span>
              <span className="due-pill">{card.response_due_date ?? "回答納期未設定"}</span>
            </div>
            <h3 className="card-customer-name">{card.customer_name || card.title}</h3>
            <div className="label-row">
              {card.labels.map((label) => (
                <span className="label-chip" key={`${card.id}-${label}`}>
                  {label}
                </span>
              ))}
              {getAgedAlert(card)?.level === 1 ? (
                <span className="label-chip alert-chip">{getAgedAlert(card)?.label}</span>
              ) : null}
              {(getAgedAlert(card)?.level ?? 0) >= 2 ? (
                <span className="label-chip alert-chip alert-chip-strong">{getAgedAlert(card)?.label}</span>
              ) : null}
              {!card.archived && canArchiveCard(card) ? (
                <span className="label-chip archivable-chip">アーカイブ可能</span>
              ) : null}
              {card.archived ? <span className="label-chip archived-chip">アーカイブ済み</span> : null}
            </div>
            <div className="meta-row">
              <span>希望納期: {card.requested_due_date ?? "未設定"}</span>
              <span>確認先: {card.assignee_name || "未設定"}</span>
            </div>
            <div className="meta-row">
              <span>確認先: {card.assignee_name || "未設定"}</span>
              <span>ステータス: {card.status}</span>
            </div>
            <div className="meta-row">
              <span>最短◎発送日: {card.earliest_ship_date ?? "未設定"}</span>
            </div>
            <div className="meta-row">
              <span>チェック {card.checklist_progress}</span>
              <span>コメント {card.comment_count}</span>
            </div>
          </article>
        ))}
      </div>

      <div className="add-card-box">
        <input
          className="add-card-input"
          placeholder="受注番号を入力して案件追加"
          value={newCardTitle}
          onChange={(event) => onChangeNewTitle(list.id, event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              void onCreateCard(list.id);
            }
          }}
        />
        <button
          className="secondary-button add-card-button"
          disabled={creatingListId === list.id}
          onClick={() => void onCreateCard(list.id)}
          type="button"
        >
          {creatingListId === list.id ? "追加中..." : "案件追加"}
        </button>
      </div>
    </section>
  );
}

export default App;
