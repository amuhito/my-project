import { FormEvent, useEffect, useState } from "react";
import { request } from "../api";
import type { AdminUser, Assignee, Meta, Tag } from "../types";

export function AdminView({ meta, onMetaChanged }: { meta: Meta; onMetaChanged: () => Promise<void> }) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [assignees, setAssignees] = useState<Assignee[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [newTag, setNewTag] = useState({ name: "", color: "#64748b" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadAdmin() {
    setError("");
    const [nextUsers, nextAssignees, nextTags] = await Promise.all([
      request<AdminUser[]>("/admin/users"),
      request<Assignee[]>("/admin/assignees"),
      request<Tag[]>("/admin/tags"),
    ]);
    setUsers(nextUsers);
    setAssignees(nextAssignees);
    setTags(nextTags);
  }

  async function run(action: () => Promise<void>) {
    setError("");
    setMessage("");
    try {
      await action();
      await loadAdmin();
      await onMetaChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function toggleUser(user: AdminUser) {
    await run(async () => {
      await request(`/admin/users/${user.id}/active`, {
        method: "PUT",
        body: JSON.stringify({ active: !user.active }),
      });
    });
  }

  async function resetPassword(user: AdminUser) {
    await run(async () => {
      const result = await request<{ temporary_password: string }>(`/admin/users/${user.id}/reset-password`, { method: "POST" });
      setMessage(`${user.display_name} の仮パスワード: ${result.temporary_password}`);
    });
  }

  async function toggleAssignee(assignee: Assignee) {
    await run(async () => {
      await request(`/admin/assignees/${assignee.id}/active`, {
        method: "PUT",
        body: JSON.stringify({ active: !assignee.active }),
      });
    });
  }

  async function createTag(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      await request("/admin/tags", { method: "POST", body: JSON.stringify(newTag) });
      setNewTag({ name: "", color: "#64748b" });
    });
  }

  async function updateTag(tag: Tag) {
    await run(async () => {
      await request(`/admin/tags/${tag.id}`, { method: "PUT", body: JSON.stringify(tag) });
    });
  }

  async function deleteTag(tag: Tag) {
    await run(async () => {
      await request(`/admin/tags/${tag.id}`, { method: "DELETE" });
    });
  }

  useEffect(() => {
    loadAdmin().catch((err) => setError(err.message));
  }, []);

  return (
    <div className="adminGrid">
      <section className="panel">
        <h2>ユーザー</h2>
        {message && <div className="notice">{message}</div>}
        {error && <div className="error">{error}</div>}
        <div className="tableScroll">
          <table>
            <thead><tr><th>ユーザー</th><th>表示名</th><th>権限</th><th>担当</th><th>状態</th><th>初回変更</th><th>操作</th></tr></thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.username}</td>
                  <td>{user.display_name}</td>
                  <td>{user.role}</td>
                  <td>{user.assignee_name ?? "-"}</td>
                  <td>{user.active ? "有効" : "無効"}</td>
                  <td>{user.password_must_change ? "必要" : "済"}</td>
                  <td className="actions">
                    <button onClick={() => toggleUser(user)}>{user.active ? "無効化" : "有効化"}</button>
                    <button onClick={() => resetPassword(user)}>リセット</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2>担当者</h2>
        <div className="list compactList">
          {assignees.map((assignee) => (
            <article key={assignee.id} className="adminItem">
              <span className="avatar" style={{ backgroundColor: assignee.color }}>{assignee.name.slice(0, 1)}</span>
              <strong>{assignee.name}</strong>
              <span>{assignee.active ? "有効" : "無効"}</span>
              <button onClick={() => toggleAssignee(assignee)}>{assignee.active ? "無効化" : "有効化"}</button>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>タグ</h2>
        <form className="inlineForm" onSubmit={createTag}>
          <input placeholder="タグ名" value={newTag.name} onChange={(event) => setNewTag({ ...newTag, name: event.target.value })} required />
          <input type="color" value={newTag.color} onChange={(event) => setNewTag({ ...newTag, color: event.target.value })} />
          <button type="submit">追加</button>
        </form>
        <div className="list compactList">
          {tags.map((tag) => (
            <article key={tag.id} className="adminItem">
              <input value={tag.name} onChange={(event) => setTags((current) => current.map((item) => item.id === tag.id ? { ...item, name: event.target.value } : item))} />
              <input type="color" value={tag.color} onChange={(event) => setTags((current) => current.map((item) => item.id === tag.id ? { ...item, color: event.target.value } : item))} />
              <button onClick={() => updateTag(tag)}>保存</button>
              <button onClick={() => deleteTag(tag)}>削除</button>
            </article>
          ))}
        </div>
        {meta.processes.length > 0 && <p className="muted">工程マスタは今回固定です。</p>}
      </section>
    </div>
  );
}
