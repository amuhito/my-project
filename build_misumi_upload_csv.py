import os
import configparser
import pandas as pd

# ========== config ==========
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

OUTPUT_FOLDER = os.path.normpath(config["paths"]["output_folder"])

# 発注CSV設定（無ければエラー）
if "orders" not in config:
    raise KeyError("config.ini に [orders] セクションがありません。order_csv 等を設定してください。")

order_csv = os.path.normpath(config["orders"]["order_csv"])
order_encoding = config["orders"].get("order_encoding", "utf-8-sig")

col_order_no   = config["orders"].getint("col_order_no", 0)
col_juchu_no   = config["orders"].getint("col_juchu_no", 1)
col_drawing_no = config["orders"].getint("col_drawing_no", 2)
col_order_code = config["orders"].getint("col_order_code", 3)
col_qty        = config["orders"].getint("col_qty", 4)
col_due        = config["orders"].getint("col_due", 6)

# 抽出結果ファイル（process_combine_matches_with_export.py の出力）
combined_path = os.path.join(OUTPUT_FOLDER, "combine_misumi_types.xlsx")

# マージ設定
min_code_len = config.getint("merge", "min_code_len", fallback=6)

# ========== helpers ==========
def is_code_sufficient(code: str) -> bool:
    if code is None:
        return False
    code = str(code).strip()
    if code == "" or code.lower() == "nan":
        return False
    return len(code) >= min_code_len

def parse_drawing_no_from_filebase(filebase: str):
    """
    filebase 例: E-25042E-2504200FG8332CZ8301A4  (拡張子なし)
    命名則: 受注番号/機械番号/種別/図番/原本区分/版数/原紙
    - 受注番号と機械番号が同一で先頭に2回続く前提。
    - 末尾は ... + 原本区分(2桁) + 版数(2桁) + 原紙(例:A4=2文字)
    返り値: 図番（例: FG8332CZ）
    """
    s = filebase
    n_total = len(s)
    rep_len = None
    for n in range(1, n_total // 2):
        if s[0:n] == s[n:2*n]:
            rep_len = n
            break
    if rep_len is None:
        return None
    tail = s[2*rep_len+2:]  # 種別(2)の後ろ＝図番+原本区分+版数+原紙
    if len(tail) < 7:
        return None
    drawing = tail[:-6]  # 図番
    return drawing or None

def split_candidates(match_str: str):
    if match_str is None:
        return []
    s = str(match_str).strip()
    if s == "" or s.lower() == "nan":
        return []
    parts = [p.strip() for p in s.split() if p.strip()]
    out = []
    seen = set()
    for p in parts:
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out

def choose_best_candidate(cands):
    """最低限のヒューリスティック：長いものを優先、次に '-' を含むもの"""
    if not cands:
        return None
    def score(x: str):
        x = str(x)
        return (len(x), 1 if "-" in x else 0, sum(ch.isdigit() for ch in x))
    return sorted(cands, key=score, reverse=True)[0]

def codes_compatible(order_code: str, cands):
    oc = str(order_code).strip()
    if oc == "" or oc.lower() == "nan":
        return False
    if oc in cands:
        return True
    for c in cands:
        if oc and oc in c:
            return True
    return False

# ========== load combined matches ==========
if not os.path.exists(combined_path):
    raise FileNotFoundError(f"抽出結果が見つかりません: {combined_path}")

df_comb = pd.read_excel(combined_path)
if not {"File Name", "Match"}.issubset(set(df_comb.columns)):
    raise ValueError("combine_misumi_types.xlsx に必要列（File Name, Match）がありません。")

# File Name から図番を作る → 図番ごとに候補を統合
drawing_to_candidates = {}

for _, row in df_comb.iterrows():
    fname = str(row["File Name"])
    match = row["Match"]
    filebase = os.path.splitext(os.path.basename(fname))[0]
    drawing = parse_drawing_no_from_filebase(filebase)
    if not drawing:
        continue
    cands = split_candidates(match)
    drawing_to_candidates.setdefault(drawing, [])
    drawing_to_candidates[drawing].extend(cands)

# 図番ごとに重複排除
for d, cands in list(drawing_to_candidates.items()):
    uniq = []
    seen = set()
    for c in cands:
        if c not in seen:
            uniq.append(c)
            seen.add(c)
    drawing_to_candidates[d] = uniq

# ========== load order csv ==========
df_order = pd.read_csv(order_csv, header=None, encoding=order_encoding, dtype=str)
max_col = max(col_order_no, col_juchu_no, col_drawing_no, col_order_code, col_qty, col_due)
if df_order.shape[1] <= max_col:
    for _ in range(max_col + 1 - df_order.shape[1]):
        df_order[df_order.shape[1]] = ""

rows_upload = []
rows_check = []

for _, r in df_order.iterrows():
    order_no = (r.iloc[col_order_no] or "").strip()
    juchu_no = (r.iloc[col_juchu_no] or "").strip()
    drawing_no = (r.iloc[col_drawing_no] or "").strip()
    order_code = (r.iloc[col_order_code] or "").strip()
    qty = (r.iloc[col_qty] or "").strip()
    due = (r.iloc[col_due] or "").strip()

    cands = drawing_to_candidates.get(drawing_no, [])
    best = choose_best_candidate(cands)

    status = ""
    final_code = order_code

    if is_code_sufficient(order_code):
        if cands:
            status = "OK" if codes_compatible(order_code, cands) else "CONFLICT"
        else:
            status = "OK_NO_DXF_CANDIDATE"
    else:
        if best:
            final_code = best
            status = "AUTO_FILLED"
        else:
            status = "MISSING"

    rows_upload.append({
        "注文No": order_no,
        "受注番号": juchu_no,
        "図番": drawing_no,
        "型式": final_code,
        "数量": qty,
        "納期": due,
    })

    rows_check.append({
        "注文No": order_no,
        "受注番号": juchu_no,
        "図番": drawing_no,
        "型式_元": order_code,
        "型式_確定": final_code,
        "数量": qty,
        "納期": due,
        "status": status,
        "候補一覧": " ".join(cands),
        "採用候補": best or "",
    })

upload_path = os.path.join(OUTPUT_FOLDER, "misumi_upload.csv")
check_path  = os.path.join(OUTPUT_FOLDER, "misumi_upload_check.csv")

pd.DataFrame(rows_upload).to_csv(upload_path, index=False, encoding="utf-8-sig")
pd.DataFrame(rows_check).to_csv(check_path, index=False, encoding="utf-8-sig")

print("Generated:")
print(" -", upload_path)
print(" -", check_path)
