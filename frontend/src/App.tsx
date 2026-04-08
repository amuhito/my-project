import { useEffect, useMemo, useState } from "react";
import { archiveCard, createCard, fetchBoard, fetchCard, moveCard, unarchiveCard } from "./api";
import { CardModal } from "./components/CardModal";
import type { BoardList, BoardResponse, CardDetail, CardSummary } from "./types";

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

function App() {
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

  useEffect(() => {
    void loadBoard();
  }, [showArchived]);

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
    } catch {
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
    } catch {
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
    } catch {
      setError("カード移動に失敗しました。");
    } finally {
      setDragState(null);
    }
  };

  const handleCardSaved = async (updatedCard: CardDetail) => {
    setActiveCard(updatedCard);
    const updatedBoard = await fetchBoard(showArchived);
    setBoard(updatedBoard);
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
    } catch {
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
    } catch {
      setError("カードの追加に失敗しました。");
    } finally {
      setCreatingListId(null);
    }
  };

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
        <button className="secondary-button" onClick={() => void loadBoard()} type="button">
          再読み込み
        </button>
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
                    <td>{card.archived ? "アーカイブ済み" : card.status}</td>
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
            className={`card-tile${card.archived ? " card-tile-archived" : ""}`}
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
