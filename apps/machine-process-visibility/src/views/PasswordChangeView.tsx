import { FormEvent, useState } from "react";
import { request } from "../api";
import type { AuthUser } from "../types";

export function PasswordChangeView({
  user,
  onChanged,
  onLogout,
}: {
  user: AuthUser;
  onChanged: (user: AuthUser) => void;
  onLogout: () => void;
}) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("確認用パスワードが一致しません");
      return;
    }
    try {
      const nextUser = await request<AuthUser>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      onChanged(nextUser);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="loginPage">
      <form className="loginBox" onSubmit={submit}>
        <h1>パスワード変更</h1>
        <p>{user.display_name} は初回パスワード変更が必要です。</p>
        <label>
          現在のパスワード
          <input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoFocus />
        </label>
        <label>
          新しいパスワード
          <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
        </label>
        <label>
          新しいパスワード確認
          <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="primary" type="submit">変更</button>
        <button type="button" onClick={onLogout}>ログアウト</button>
      </form>
    </div>
  );
}
