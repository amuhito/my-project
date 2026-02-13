import os
import configparser
import pandas as pd
import logging


import re

def normalize(s: str) -> str:
    return str(s or "").strip()

def detect_machine_no_from_filename(filebase: str, order_no: str):
    '''
    Try to detect machine_no if not provided.
    Expect filebase starts with order_no + <machine_no> ...
    machine_no pattern: [A-Z]-\d{5} (e.g., E-25042, P-55998, S-25034)
    '''
    s = filebase
    if not s.startswith(order_no):
        return None
    rest = s[len(order_no):]
    m = re.match(r"([A-Z]-\d{5})", rest)
    return m.group(1) if m else None

def parse_filebase_misumi(filebase: str, order_no: str, machine_no: str | None):
    '''
    Parse filebase (no extension) according to naming convention:
      受注番号 / 機械番号 / 種別(2) / 図番 / 原本区分(2) / 版数(2) / 原紙(例:A4)
    Stored without separators, e.g.:
      E-25042E-2504200FG8332CZ8301A4
    Returns dict with keys:
      order_no, machine_no, kind, drawing_no, original_class, revision, paper
    or None if not parseable.
    '''
    s = filebase
    if not order_no:
        return None
    if not s.startswith(order_no):
        return None

    if machine_no:
        if not s.startswith(order_no + machine_no):
            return None
        pos = len(order_no + machine_no)
    else:
        if s.startswith(order_no + order_no):
            machine_no = order_no
            pos = len(order_no + order_no)
        else:
            detected = detect_machine_no_from_filename(s, order_no)
            if not detected:
                return None
            machine_no = detected
            pos = len(order_no) + len(machine_no)

    if len(s) < pos + 2 + 6:
        return None

    kind = s[pos:pos+2]
    tail = s[pos+2:]

    if len(tail) < 6:
        return None
    paper = tail[-2:]
    rev = tail[-4:-2]
    original_class = tail[-6:-4]
    drawing_no = tail[:-6]

    if not drawing_no:
        return None

    return {
        "order_no": order_no,
        "machine_no": machine_no,
        "kind": kind,
        "drawing_no": drawing_no,
        "original_class": original_class,
        "revision": rev,
        "paper": paper,
    }

def load_config():
    config = configparser.ConfigParser()
    here = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(here, "config.ini")
    config.read(config_path, encoding="utf-8")
    return config, here

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
    if not cands:
        return None
    def score(x: str):
        x = str(x)
        return (len(x), 1 if "-" in x else 0, sum(ch.isdigit() for ch in x))
    return sorted(cands, key=score, reverse=True)[0]

def is_blank(code: str) -> bool:
    if code is None:
        return True
    s = str(code).strip()
    return s == "" or s.lower() == "nan"

def is_likely_truncated(code: str, min_len: int) -> bool:
    s = str(code or "").strip()
    if not s:
        return False
    if s.endswith(("-", "+", "/", "_")):
        return True
    if len(s) < min_len:
        return True
    return False

def list_pdfs(input_folder: str):
    return [fn for fn in os.listdir(input_folder) if fn.lower().endswith(".pdf") and os.path.isfile(os.path.join(input_folder, fn))]

def list_dxfs(input_folder: str):
    return [fn for fn in os.listdir(input_folder) if fn.lower().endswith(".dxf") and os.path.isfile(os.path.join(input_folder, fn))]

def build_pdf_drawing_set(input_folder: str, order_no: str, machine_no: str | None):
    pdfs = list_pdfs(input_folder)
    drawings = set()
    for fn in pdfs:
        base = os.path.splitext(os.path.basename(fn))[0]
        info = parse_filebase_misumi(base, order_no, machine_no)
        if info:
            drawings.add(info["drawing_no"])
    return drawings

def build_dxf_drawing_set(input_folder: str, order_no: str, machine_no: str | None):
    dxfs = list_dxfs(input_folder)
    drawings = set()
    for fn in dxfs:
        base = os.path.splitext(os.path.basename(fn))[0]
        info = parse_filebase_misumi(base, order_no, machine_no)
        if info:
            drawings.add(info["drawing_no"])
    return drawings

def resolve_order_row(order_code: str, cands: list[str], has_dxf: bool):
    """
    AUTO/REVIEW/ERROR を明確に分離して判定する。
    AUTO は「一意候補のみ」。
    短縮型式補完（prefix補完）は DXF が存在する場合のみ実施する。
    """
    if is_blank(order_code):
        if len(cands) == 1:
            return "AUTO", "BLANK_ORDER_CODE_SINGLE_CANDIDATE", cands[0]
        if len(cands) == 0:
            return "REVIEW", "BLANK_ORDER_CODE_NO_CANDIDATE", ""
        return "REVIEW", "BLANK_ORDER_CODE_MULTI_CANDIDATE", ""

    if order_code in cands:
        return "REVIEW", "ORDER_CODE_MATCHED", ""

    if has_dxf:
        prefix_hits = [c for c in cands if c.startswith(order_code) and len(c) > len(order_code)]
        if len(prefix_hits) == 1:
            return "AUTO", "PREFIX_COMPLETION_SINGLE_CANDIDATE", prefix_hits[0]
        if len(prefix_hits) >= 2:
            return "REVIEW", "PREFIX_COMPLETION_MULTI_CANDIDATE", ""

    if len(cands) == 0:
        return "REVIEW", "ORDER_CODE_MISMATCH_NO_CANDIDATE", ""
    return "REVIEW", "ORDER_CODE_MISMATCH_MULTI_OR_DIFFERENT", ""

def load_candidates_xlsx(output_folder: str, order_no: str, machine_no: str | None):
    combined_path = os.path.join(output_folder, "combine_misumi_types.xlsx")
    if not os.path.exists(combined_path):
        raise FileNotFoundError(f"抽出結果が見つかりません: {combined_path}")

    df = pd.read_excel(combined_path)
    need_cols = {"File Name", "Match"}
    if not need_cols.issubset(set(df.columns)):
        raise ValueError("combine_misumi_types.xlsx に必要列（File Name, Match）がありません。")

    drawing_to_candidates = {}
    for _, row in df.iterrows():
        fname = str(row["File Name"])
        match = row["Match"]
        filebase = os.path.splitext(os.path.basename(fname))[0]
        info = parse_filebase_misumi(filebase, order_no, machine_no)
        if not info:
            continue
        drawing = info["drawing_no"]
        cands = split_candidates(match)
        if not cands:
            continue
        drawing_to_candidates.setdefault(drawing, [])
        drawing_to_candidates[drawing].extend(cands)

    for d, cands in list(drawing_to_candidates.items()):
        uniq = []
        seen = set()
        for c in cands:
            if c not in seen:
                uniq.append(c)
                seen.add(c)
        drawing_to_candidates[d] = uniq
    return drawing_to_candidates

def main():
    logging.basicConfig(level=logging.INFO)
    config, _ = load_config()

    output_folder = os.path.normpath(config["paths"]["output_folder"])
    input_folder = os.path.normpath(config["paths"]["input_folder"])
    os.makedirs(output_folder, exist_ok=True)

    mode = config.get("run", "mode", fallback="pre").strip().lower()
    order_no = config.get("run", "order_no", fallback="").strip()
    machine_no = config.get("run", "machine_no", fallback="").strip() or None

    if not order_no:
        order_no = input("受注番号を入力してください（例: E-25049）: ").strip()
    if machine_no is None:
        tmp = input("機械番号を入力してください（任意、例: P-55998。空でスキップ）: ").strip()
        machine_no = tmp or None

    drawing_to_candidates = load_candidates_xlsx(output_folder, order_no, machine_no)
    drawings_with_pdf = build_pdf_drawing_set(input_folder, order_no, machine_no)
    drawings_with_dxf = build_dxf_drawing_set(input_folder, order_no, machine_no)

    if mode == "order":
        if "orders" not in config:
            raise KeyError("ORDERモードでは config.ini に [orders] が必要です（order_csv, order_sep, col_*）")

        order_csv = os.path.normpath(config["orders"]["order_csv"])
        order_encoding = config["orders"].get("order_encoding", "utf-8-sig")
        order_sep = config["orders"].get("order_sep", "\t")

        col_order_no   = config["orders"].getint("col_order_no", 0)
        col_juchu_no   = config["orders"].getint("col_juchu_no", 1)
        col_drawing_no = config["orders"].getint("col_drawing_no", 2)
        col_order_code = config["orders"].getint("col_order_code", 3)

        df_order = pd.read_csv(order_csv, header=None, encoding=order_encoding, dtype=str, sep=order_sep)

        max_col = max(col_order_no, col_juchu_no, col_drawing_no, col_order_code)
        if df_order.shape[1] <= max_col:
            raise ValueError(f"発注CSVの列数が不足しています。必要={max_col+1}列, actual={df_order.shape[1]}列")

        rows = []
        for idx, row in df_order.iterrows():
            drawing = normalize(row.iloc[col_drawing_no])
            order_code = normalize(row.iloc[col_order_code])
            cands = drawing_to_candidates.get(drawing, [])
            has_pdf = drawing in drawings_with_pdf
            has_dxf = drawing in drawings_with_dxf

            if not drawing:
                status, reason_code, proposed = "ERROR", "DRAWING_NO_BLANK", ""
            else:
                status, reason_code, proposed = resolve_order_row(order_code, cands, has_dxf)

            rows.append({
                "row_index": idx,
                "order_no": normalize(row.iloc[col_order_no]),
                "juchu_no": normalize(row.iloc[col_juchu_no]),
                "drawing_no": drawing,
                "order_code": order_code,
                "has_pdf": has_pdf,
                "has_dxf": has_dxf,
                "candidates": "|".join(cands),
                "status": status,
                "reason_code": reason_code,
                "proposed_code": proposed,
            })
            logging.info(
                "row_index=%s drawing_no=%s status=%s reason_code=%s has_pdf=%s has_dxf=%s candidates=%s proposed=%s",
                idx, drawing, status, reason_code, has_pdf, has_dxf, "|".join(cands), proposed
            )

        df_check = pd.DataFrame(rows)
        check_path = os.path.join(output_folder, "check.csv")
        df_check.to_csv(check_path, index=False, encoding="utf-8-sig")

        df_upload = df_order.copy()
        for r in rows:
            if r["status"] == "AUTO" and r["proposed_code"]:
                df_upload.iat[r["row_index"], col_order_code] = r["proposed_code"]

        upload_path = os.path.join(output_folder, "upload.csv")
        df_upload.to_csv(upload_path, index=False, header=False, encoding="utf-8-sig")

        print(f"Saved: {check_path}")
        print(f"Saved: {upload_path}")
        print("AUTO件数:", int((df_check["status"] == "AUTO").sum()))
        print("REVIEW件数:", int((df_check["status"] == "REVIEW").sum()))
        print("ERROR件数:", int((df_check["status"] == "ERROR").sum()))

    else:
        out_rows = []
        for drawing, cands in sorted(drawing_to_candidates.items(), key=lambda x: x[0]):
            best = choose_best_candidate(cands)
            has_pdf = drawing in drawings_with_pdf
            status = "AUTO" if has_pdf and len(cands) == 1 else "REVIEW"
            reason_code = (
                "SINGLE_CANDIDATE_WITH_PDF" if has_pdf and len(cands) == 1
                else "MULTI_CANDIDATE_WITH_PDF" if has_pdf and len(cands) > 1
                else "NO_PDF_OR_NO_CANDIDATE"
            )
            out_rows.append({
                "drawing_no": drawing,
                "has_pdf": has_pdf,
                "candidates": "|".join(cands),
                "best_candidate": best or "",
                "status": status,
                "reason_code": reason_code,
            })
        df_sum = pd.DataFrame(out_rows)
        sum_path = os.path.join(output_folder, "candidates_summary.csv")
        df_sum.to_csv(sum_path, index=False, encoding="utf-8-sig")
        print(f"Saved: {sum_path}")

if __name__ == "__main__":
    main()
