import os
import logging
import configparser
from PyPDF2 import PdfReader, PdfWriter


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

def list_pdfs(folder: str):
    return [fn for fn in os.listdir(folder) if fn.lower().endswith(".pdf") and os.path.isfile(os.path.join(folder, fn))]

def build_pdf_index(pdf_names, order_no: str, machine_no: str | None):
    idx = {}
    meta = {}
    for fn in pdf_names:
        base = os.path.splitext(os.path.basename(fn))[0]
        info = parse_filebase_misumi(base, order_no, machine_no)
        if not info:
            continue
        meta[fn] = info
        idx.setdefault(info["drawing_no"], []).append(fn)
    for d, fns in idx.items():
        fns.sort(key=lambda x: x.lower())
    return idx, meta

def read_ordered_drawings(config):
    if "orders" not in config:
        raise KeyError("ORDERモードでは config.ini に [orders] が必要です（order_csv, order_sep, col_drawing_no など）")
    import pandas as pd
    order_csv = os.path.normpath(config["orders"]["order_csv"])
    order_encoding = config["orders"].get("order_encoding", "utf-8-sig")
    order_sep = config["orders"].get("order_sep", "\t")
    col_drawing_no = config["orders"].getint("col_drawing_no", 2)
    df = pd.read_csv(order_csv, header=None, encoding=order_encoding, dtype=str, sep=order_sep)
    if df.shape[1] <= col_drawing_no:
        raise ValueError(f"発注CSVの列数が不足しています。col_drawing_no={col_drawing_no}, actual_cols={df.shape[1]}")
    drawings = [normalize(v) for v in df.iloc[:, col_drawing_no].tolist()]
    return [d for d in drawings if d]

def combine_in_order(input_folder, ordered_pdf_filenames, output_pdf_path):
    writer = PdfWriter()
    for fn in ordered_pdf_filenames:
        file_path = os.path.join(input_folder, fn)
        logging.info(f"Add PDF: {fn}")
        with open(file_path, "rb") as f:
            r = PdfReader(f)
            for page in r.pages:
                writer.add_page(page)
    with open(output_pdf_path, "wb") as out:
        writer.write(out)

def main():
    config, _ = load_config()
    logging.basicConfig(level=logging.INFO)

    input_folder = os.path.normpath(config["paths"]["input_folder"])
    output_folder = os.path.normpath(config["paths"]["output_folder"])
    os.makedirs(output_folder, exist_ok=True)

    mode = config.get("run", "mode", fallback="pre").strip().lower()
    order_no = config.get("run", "order_no", fallback="").strip()
    machine_no = config.get("run", "machine_no", fallback="").strip() or None

    if not order_no:
        order_no = input("受注番号を入力してください（例: E-25049）: ").strip()
    if machine_no is None:
        tmp = input("機械番号を入力してください（任意、例: P-55998。空でスキップ）: ").strip()
        machine_no = tmp or None

    pdf_names = list_pdfs(input_folder)
    idx, meta = build_pdf_index(pdf_names, order_no, machine_no)

    if mode == "order":
        drawings = read_ordered_drawings(config)
        ordered = []
        added = set()
        missing = []
        multi = []
        for d in drawings:
            hits = idx.get(d, [])
            if not hits:
                missing.append(d)
                continue
            if len(hits) > 1:
                multi.append((d, hits))
            for fn in hits:
                if fn in added:
                    continue
                ordered.append(fn)
                added.add(fn)
        out_path = os.path.join(output_folder, "combine_misumi_ordered.pdf")
        combine_in_order(input_folder, ordered, out_path)
        logging.info(f"Saved: {out_path}")
        if missing:
            logging.warning("PDFが見つからない図番（%d件）: %s", len(missing), ", ".join(missing[:50]) + (" ..." if len(missing) > 50 else ""))
        if multi:
            logging.warning("同一図番で複数PDFヒット（%d件）: 先頭20件を表示", len(multi))
            for d, h in multi[:20]:
                logging.warning("  - %s: %s", d, h)
    else:
        sortable = []
        for fn, info in meta.items():
            sortable.append((info["drawing_no"], info["kind"], info["original_class"], info["revision"], fn.lower(), fn))
        sortable.sort()
        ordered = [t[-1] for t in sortable]
        out_path = os.path.join(output_folder, "combine_misumi_pre.pdf")
        combine_in_order(input_folder, ordered, out_path)
        logging.info(f"Saved: {out_path}")

if __name__ == "__main__":
    main()
