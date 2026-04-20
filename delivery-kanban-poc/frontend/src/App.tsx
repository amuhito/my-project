import { useEffect, useMemo, useState } from "react";
import {
  clearStoredAuthToken,
  createInquiry,
  createUser,
  fetchCurrentUser,
  fetchInquiry,
  fetchInquiries,
  fetchInquiryItem,
  fetchKanban,
  fetchUsers,
  getStoredAuthToken,
  login,
  moveInquiryItem,
} from "./api";
import { InquiryItemModal } from "./components/InquiryItemModal";
import type {
  AuthUser,
  InquiryDetail,
  InquiryItemDetail,
  InquiryItemSummary,
  InquirySummary,
  KanbanColumn,
} from "./types";

type PageMode = "inquiries" | "new-inquiry" | "inquiry-detail" | "kanban";

type DragState = {
  itemId: number;
  sourceProcess: InquiryItemSummary["process"];
};

function isUnauthorizedError(error: unknown) {
  return error instanceof Error && error.message === "UNAUTHORIZED";
}

function formatDateText(value: string | null) {
  if (!value) {
    return "-";
  }
  return value.slice(0, 10);
}

function toShortCustomerName(value: string) {
  if (value.length <= 12) {
    return value;
  }
  return `${value.slice(0, 12)}…`;
}

function normalizeKanbanColumns(columns: KanbanColumn[]): KanbanColumn[] {
  const visibleColumns = columns
    .filter((column) => column.process !== "sales_registered")
    .map((column) => ({
      ...column,
      items: [...column.items],
    }));
  const salesRegisteredItems =
    columns.find((column) => column.process === "sales_registered")?.items ?? [];
  if (salesRegisteredItems.length === 0) {
    return visibleColumns;
  }

  const notDrawnColumn = visibleColumns.find((column) => column.process === "not_drawn");
  if (!notDrawnColumn) {
    return visibleColumns;
  }
  notDrawnColumn.items = [...salesRegisteredItems, ...notDrawnColumn.items];
  return visibleColumns;
}

function App() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [pageMode, setPageMode] = useState<PageMode>("inquiries");
  const [inquiries, setInquiries] = useState<InquirySummary[]>([]);
  const [inquiryDetail, setInquiryDetail] = useState<InquiryDetail | null>(null);
  const [kanbanColumns, setKanbanColumns] = useState<KanbanColumn[]>([]);
  const [dragState, setDragState] = useState<DragState | null>(null);

  const [activeItem, setActiveItem] = useState<InquiryItemDetail | null>(null);
  const [itemModalOpen, setItemModalOpen] = useState(false);

  const [userModalOpen, setUserModalOpen] = useState(false);
  const [managedUsers, setManagedUsers] = useState<AuthUser[]>([]);
  const [userManageLoading, setUserManageLoading] = useState(false);
  const [userManageError, setUserManageError] = useState("");

  useEffect(() => {
    void restoreSession();
  }, []);

  useEffect(() => {
    if (!currentUser) {
      setLoading(false);
      return;
    }
    void loadBaseData();
  }, [currentUser]);

  const kanbanLookup = useMemo(() => {
    const map = new Map<number, InquiryItemSummary["process"]>();
    kanbanColumns.forEach((column) => {
      column.items.forEach((item) => {
        map.set(item.id, item.process);
      });
    });
    return map;
  }, [kanbanColumns]);

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

  const loadBaseData = async () => {
    try {
      setLoading(true);
      setError("");
      const [inquiryList, kanban] = await Promise.all([fetchInquiries(), fetchKanban()]);
      setInquiries(inquiryList.inquiries);
      setKanbanColumns(normalizeKanbanColumns(kanban.columns));
    } catch (loadError) {
      if (isUnauthorizedError(loadError)) {
        handleLogout();
        return;
      }
      setError("データ取得に失敗しました。バックエンド起動状態を確認してください。");
    } finally {
      setLoading(false);
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
    setPageMode("inquiries");
    setInquiryDetail(null);
    setItemModalOpen(false);
    setActiveItem(null);
    setError("");
  };

  const openInquiryDetail = async (inquiryId: number) => {
    try {
      setError("");
      const detail = await fetchInquiry(inquiryId);
      setInquiryDetail(detail);
      setPageMode("inquiry-detail");
    } catch (loadError) {
      if (isUnauthorizedError(loadError)) {
        handleLogout();
        return;
      }
      setError("問い合わせ詳細の取得に失敗しました。");
    }
  };

  const openItemModal = async (itemId: number) => {
    try {
      setError("");
      const detail = await fetchInquiryItem(itemId);
      setActiveItem(detail);
      setItemModalOpen(true);
    } catch (loadError) {
      if (isUnauthorizedError(loadError)) {
        handleLogout();
        return;
      }
      setError("子案件の取得に失敗しました。");
    }
  };

  const handleItemSaved = async (updatedItem: InquiryItemDetail) => {
    setActiveItem(updatedItem);
    setItemModalOpen(false);
    await loadBaseData();
    if (inquiryDetail) {
      await openInquiryDetail(inquiryDetail.id);
    }
  };

  const handleDrop = async (destinationProcess: InquiryItemSummary["process"], destinationIndex: number) => {
    if (!dragState) {
      return;
    }

    try {
      setError("");
      const updated = await moveInquiryItem({
        item_id: dragState.itemId,
        destination_process: destinationProcess,
        destination_index: destinationIndex,
      });
      setKanbanColumns(normalizeKanbanColumns(updated.columns));
      if (inquiryDetail) {
        const refreshed = await fetchInquiry(inquiryDetail.id);
        setInquiryDetail(refreshed);
      }
    } catch (moveError) {
      if (isUnauthorizedError(moveError)) {
        handleLogout();
        return;
      }
      setError(moveError instanceof Error ? moveError.message : "移動に失敗しました。");
    } finally {
      setDragState(null);
    }
  };

  const loadManagedUsers = async () => {
    try {
      setUserManageLoading(true);
      setUserManageError("");
      const users = await fetchUsers();
      setManagedUsers(users);
    } catch (loadError) {
      if (isUnauthorizedError(loadError)) {
        handleLogout();
        return;
      }
      setUserManageError(loadError instanceof Error ? loadError.message : "ユーザー一覧の取得に失敗しました。");
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
          <div className="hero-badge">フェーズ1-A</div>
          <h1>納期管理カンバン</h1>
          <p>親: 問い合わせ / 子: 案件（P/E/S）で管理します。</p>
        </div>
        <div className="hero-actions">
          <div className="login-user-chip">{currentUser.display_name}</div>
          {currentUser.username === "admin" ? (
            <button className="secondary-button" onClick={() => void openUserManagement()} type="button">
              ユーザー管理
            </button>
          ) : null}
          <button className="secondary-button" onClick={() => void loadBaseData()} type="button">
            再読み込み
          </button>
          <button className="ghost-button" onClick={handleLogout} type="button">
            ログアウト
          </button>
        </div>
      </header>

      <nav className="page-tabs">
        <button
          className={pageMode === "inquiries" ? "primary-button" : "ghost-button"}
          onClick={() => setPageMode("inquiries")}
          type="button"
        >
          問い合わせ一覧
        </button>
        <button
          className={pageMode === "new-inquiry" ? "primary-button" : "ghost-button"}
          onClick={() => setPageMode("new-inquiry")}
          type="button"
        >
          新規問い合わせ
        </button>
        <button
          className={pageMode === "kanban" ? "primary-button" : "ghost-button"}
          onClick={() => setPageMode("kanban")}
          type="button"
        >
          子案件カンバン
        </button>
      </nav>

      {error ? <div className="error-banner">{error}</div> : null}

      {pageMode === "inquiries" ? (
        <InquiryListSection inquiries={inquiries} onOpenDetail={(inquiryId) => void openInquiryDetail(inquiryId)} />
      ) : null}

      {pageMode === "new-inquiry" ? (
        <InquiryCreateSection
          onCreated={async (detail) => {
            await loadBaseData();
            setInquiryDetail(detail);
            setPageMode("inquiry-detail");
          }}
          onError={(message) => setError(message)}
        />
      ) : null}

      {pageMode === "inquiry-detail" && inquiryDetail ? (
        <InquiryDetailSection inquiry={inquiryDetail} onEditItem={(itemId) => void openItemModal(itemId)} />
      ) : null}

      {pageMode === "kanban" ? (
        <KanbanSection
          columns={kanbanColumns}
          lookup={kanbanLookup}
          onDrop={handleDrop}
          onOpenItem={(itemId) => void openItemModal(itemId)}
          onStartDrag={setDragState}
        />
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

      <InquiryItemModal
        item={activeItem}
        open={itemModalOpen}
        onClose={() => setItemModalOpen(false)}
        onSaved={(updated) => void handleItemSaved(updated)}
      />
    </div>
  );
}

type InquiryListSectionProps = {
  inquiries: InquirySummary[];
  onOpenDetail: (inquiryId: number) => void;
};

function InquiryListSection({ inquiries, onOpenDetail }: InquiryListSectionProps) {
  return (
    <section className="table-panel">
      <table className="case-table">
        <thead>
          <tr>
            <th>問い合わせID</th>
            <th>納入先</th>
            <th>希望納期</th>
            <th>依頼内容</th>
            <th>案件件数</th>
            <th>作成日</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {inquiries.map((inquiry) => (
            <tr key={inquiry.id}>
              <td>{inquiry.display_id}</td>
              <td>{inquiry.customer_name}</td>
              <td>{inquiry.requested_due_display}</td>
              <td>{inquiry.request_kind_label}</td>
              <td>{inquiry.item_count}</td>
              <td>{formatDateText(inquiry.created_at)}</td>
              <td>
                <button className="secondary-button" onClick={() => onOpenDetail(inquiry.id)} type="button">
                  詳細
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

type InquiryCreateSectionProps = {
  onCreated: (detail: InquiryDetail) => Promise<void>;
  onError: (message: string) => void;
};

function InquiryCreateSection({ onCreated, onError }: InquiryCreateSectionProps) {
  const [customerName, setCustomerName] = useState("");
  const [orderNos, setOrderNos] = useState("");
  const [requestedDueType, setRequestedDueType] = useState<"shortest" | "specific">("shortest");
  const [requestedDueDate, setRequestedDueDate] = useState("");
  const [requestKind, setRequestKind] = useState<"confirm" | "shorten">("confirm");
  const [remarks, setRemarks] = useState("");
  const [saving, setSaving] = useState(false);
  const [localError, setLocalError] = useState("");

  const submit = async () => {
    if (!customerName.trim()) {
      setLocalError("納入先は必須です。");
      return;
    }
    if (!orderNos.trim()) {
      setLocalError("受注Noは必須です。");
      return;
    }
    if (requestedDueType === "specific" && !requestedDueDate) {
      setLocalError("指定日の場合は日付を入力してください。");
      return;
    }

    try {
      setSaving(true);
      setLocalError("");
      onError("");
      const created = await createInquiry({
        customer_name: customerName,
        order_nos: orderNos,
        requested_due_type: requestedDueType,
        requested_due_date: requestedDueType === "specific" ? requestedDueDate : null,
        request_kind: requestKind,
        remarks,
      });
      await onCreated(created);
      setCustomerName("");
      setOrderNos("");
      setRequestedDueType("shortest");
      setRequestedDueDate("");
      setRequestKind("confirm");
      setRemarks("");
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "問い合わせ作成に失敗しました。";
      setLocalError(message);
      onError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="panel create-panel">
      <h2>新規問い合わせ作成</h2>
      {localError ? <div className="error-banner">{localError}</div> : null}
      <div className="row-fields row-fields-2">
        <label className="field">
          <span>納入先（必須）</span>
          <input value={customerName} onChange={(event) => setCustomerName(event.target.value)} />
        </label>
        <label className="field">
          <span>依頼内容</span>
          <select value={requestKind} onChange={(event) => setRequestKind(event.target.value as "confirm" | "shorten")}>
            <option value="confirm">納期確認</option>
            <option value="shorten">納期短縮</option>
          </select>
        </label>
      </div>

      <label className="field">
        <span>受注No（必須・複数可）</span>
        <textarea
          rows={6}
          placeholder={"P-61057\nE-12345,S-99881\nP-61057～63"}
          value={orderNos}
          onChange={(event) => setOrderNos(event.target.value)}
        />
      </label>

      <div className="row-fields row-fields-2">
        <label className="field">
          <span>希望納期種別</span>
          <select
            value={requestedDueType}
            onChange={(event) => setRequestedDueType(event.target.value as "shortest" | "specific")}
          >
            <option value="shortest">最短</option>
            <option value="specific">指定日</option>
          </select>
        </label>
        {requestedDueType === "specific" ? (
          <label className="field">
            <span>希望納期（日付）</span>
            <input
              type="date"
              value={requestedDueDate}
              onChange={(event) => setRequestedDueDate(event.target.value)}
            />
          </label>
        ) : (
          <div />
        )}
      </div>

      <label className="field">
        <span>備考</span>
        <textarea rows={4} value={remarks} onChange={(event) => setRemarks(event.target.value)} />
      </label>

      <div className="modal-footer">
        <button className="primary-button" disabled={saving} onClick={() => void submit()} type="button">
          {saving ? "作成中..." : "問い合わせを作成"}
        </button>
      </div>
    </section>
  );
}

type InquiryDetailSectionProps = {
  inquiry: InquiryDetail;
  onEditItem: (itemId: number) => void;
};

function InquiryDetailSection({ inquiry, onEditItem }: InquiryDetailSectionProps) {
  return (
    <section className="panel">
      <h2>問い合わせ詳細 {inquiry.display_id}</h2>
      <div className="detail-grid">
        <div>
          <strong>納入先:</strong> {inquiry.customer_name}
        </div>
        <div>
          <strong>希望納期:</strong> {inquiry.requested_due_display}
        </div>
        <div>
          <strong>依頼内容:</strong> {inquiry.request_kind_label}
        </div>
        <div>
          <strong>作成日:</strong> {formatDateText(inquiry.created_at)}
        </div>
        <div className="detail-wide">
          <strong>備考:</strong> {inquiry.remarks || "-"}
        </div>
      </div>

      <h3>子案件一覧</h3>
      <table className="case-table">
        <thead>
          <tr>
            <th>種別</th>
            <th>番号</th>
            <th>工程</th>
            <th>担当</th>
            <th>希望納期</th>
            <th>確定納期</th>
            <th>状態</th>
            <th>更新日</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {inquiry.items.map((item) => (
            <tr key={item.id}>
              <td>{item.item_type}</td>
              <td>{item.item_no}</td>
              <td>{item.process_label}</td>
              <td>{item.owner || "-"}</td>
              <td>{inquiry.requested_due_display}</td>
              <td>{formatDateText(item.confirmed_shipping_date)}</td>
              <td>{item.state_label}</td>
              <td>{formatDateText(item.updated_at)}</td>
              <td>
                <button className="secondary-button" onClick={() => onEditItem(item.id)} type="button">
                  編集
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

type KanbanSectionProps = {
  columns: KanbanColumn[];
  lookup: Map<number, InquiryItemSummary["process"]>;
  onDrop: (destinationProcess: InquiryItemSummary["process"], destinationIndex: number) => Promise<void>;
  onOpenItem: (itemId: number) => void;
  onStartDrag: (state: DragState) => void;
};

function KanbanSection({ columns, lookup, onDrop, onOpenItem, onStartDrag }: KanbanSectionProps) {
  return (
    <main className="board board-6">
      {columns.map((column) => (
        <section
          key={column.process}
          className="list-column"
          onDragOver={(event) => event.preventDefault()}
          onDrop={() => void onDrop(column.process, column.items.length)}
        >
          <div className="list-header">
            <h2>{column.label}</h2>
            <span>{column.items.length} 件</span>
          </div>

          <div className="card-list">
            {column.items.map((item, index) => (
              <article
                className="card-tile"
                draggable
                key={item.id}
                onClick={() => onOpenItem(item.id)}
                onDragStart={() =>
                  onStartDrag({
                    itemId: item.id,
                    sourceProcess: lookup.get(item.id) ?? item.process,
                  })
                }
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  void onDrop(column.process, index);
                }}
              >
                <div className="card-topline">
                  <span className="label-chip type-chip">{item.item_type}</span>
                  <span className="card-order-no">{item.item_no}</span>
                </div>
                <div className="label-row">
                  <span className={`label-chip ${item.request_kind === "shorten" ? "danger-chip" : "info-chip"}`}>
                    {item.request_kind_label}
                  </span>
                </div>
                <h3 className="card-customer-name">{toShortCustomerName(item.customer_name)}</h3>
                <div className="meta-row">
                  <span>担当: {item.owner || "未設定"}</span>
                  <span>希望納期: {item.requested_due_display}</span>
                </div>
                <div className="meta-row">
                  <span>状態: {item.state_label}</span>
                </div>
              </article>
            ))}
          </div>
        </section>
      ))}
    </main>
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
        <h1>納期管理カンバン</h1>
        <p>ログインしてください。</p>
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
      setFormError(submitError instanceof Error ? submitError.message : "ユーザー作成に失敗しました。");
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

export default App;
