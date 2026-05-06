import { FormEvent, useState } from "react";

export function LoginView({ error, onLogin }: { error: string; onLogin: (username: string, password: string) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

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
      </form>
    </div>
  );
}
