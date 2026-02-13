import os
import re
import logging
import configparser
from PyPDF2 import PdfReader, PdfWriter

def load_config():
    config = configparser.ConfigParser()
    here = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(here, "config.ini")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config.ini が見つかりません: {config_path}")
    config.read(config_path, encoding="utf-8")
    return config, here

def normalize(s: str) -> str:
    return str(s or "").strip()

ORDER_NO_RE = re.compile(r"^[A-Z]-\d{5}$", re.IGNORECASE)  # E-25085 等

def prompt_order_machine(config):
    default_order = normalize(config.get("run", "order_no", fallback=""))
    default_machine = normalize(config.get("run", "machine_no", fallback=""))

    while True:
        msg = "受注番号を入力してください（例: E-25049）"
        if default_order:
            msg += f" [Enterで {default_order}]"
        msg += ": "
        order_no = input(msg).strip()
        if not order_no and default_order:
            order_no = default_order
        order_no = normalize(order_no)

        if ORDER_NO_RE.match(order_no):
            break
        print("受注番号の形式が不正です。例: E-25049 の形式で入力してください。")

    msg = "機械番号を入力してください（任意、例: P-55998。空でスキップ）"
    if default_machine:
        msg += f" [Enterで {default_machine}]"
    msg += ": "
    machine_no = input(msg).strip()
    if not machine_no and default_machine:
        machine_no = default_machine
    machine_no = normalize(machine_no)

    return order_no, machine_no

def list_pdfs(input_folder: str):
    if not os.path.isdir(input_folder):
        return []
    return [
        fn for fn in os.listdir(input_folder)
        if fn.lower().endswith(".pdf") and os.path.isfile(os.path.join(input_folder, fn))
    ]

def match_pdfs_for_drawing(pdf_names, drawing_no: str, order_no: str, machine_no: str):
    '''
    誤爆防止のため、段階フィルタで絞る:
      1) 受注番号を含む
      2) (任意) 機械番号を含む
      3) 図番を含む（命名則に寄せて、図番直後が2桁数字 or 拡張子 のものを優先）
    '''
    dn = normalize(drawing_no)
    if not dn:
        return []

    dn_low = dn.lower()
    order_low = normalize(order_no).lower()
    machine_low = normalize(machine_no).lower()

    scoped = [p for p in pdf_names if order_low in p.lower()]
    if machine_low:
        scoped = [p for p in scoped if machine_low in p.lower()]

    hits = []
    for p in scoped:
        pl = p.lower()
        idx = pl.find(dn_low)
        if idx < 0:
            continue
        after = pl[idx + len(dn_low):]
        if re.match(r"^\d{2}", after) or after.startswith(".pdf"):
            hits.append(p)
        else:
            hits.append(p)

    return sorted(set(hits), key=lambda x: x.lower())

def read_ordered_drawings(config):
    '''
    orders.order_csv が未設定/ダミーの場合は起動時にパス入力させる。
    '''
    if "orders" not in config:
        raise KeyError("config.ini に [orders] がありません（order_csv, col_drawing_no, order_sep を設定してください）")

    order_csv = normalize(config["orders"].get("order_csv", ""))
    if not order_csv or "path\\to\\your" in order_csv.lower():
        order_csv = normalize(input("注文CSVのパスを入力してください（例: C:\\...\\E-25085.csv）: "))

    order_csv = os.path.normpath(order_csv)
    if not os.path.exists(order_csv):
        raise FileNotFoundError(f"注文CSVが見つかりません: {order_csv}")

    order_encoding = config["orders"].get("order_encoding", "utf-8-sig")

    order_sep_raw = config["orders"].get("order_sep", "\\t")
    order_sep = "\t" if order_sep_raw in ["\\t", "TAB", "tab"] else order_sep_raw

    col_drawing_no = config["orders"].getint("col_drawing_no", 2)

    import pandas as pd
    df = pd.read_csv(order_csv, header=None, encoding=order_encoding, dtype=str, sep=order_sep, engine="python")

    if df.shape[1] <= col_drawing_no:
        raise ValueError(f"発注CSVの列数が不足しています。col_drawing_no={col_drawing_no}, actual_cols={df.shape[1]}")

    drawings = [normalize(v) for v in df.iloc[:, col_drawing_no].tolist()]
    return [d for d in drawings if d]

def combine_pdfs_order_mode(config, input_folder, output_folder, order_no, machine_no):
    os.makedirs(output_folder, exist_ok=True)
    output_pdf_path = os.path.join(output_folder, "combine_misumi_ordered.pdf")

    pdf_names = list_pdfs(input_folder)
    if not pdf_names:
        logging.warning("input_folder にPDFが見つかりません。")
        return

    drawings = read_ordered_drawings(config)

    writer = PdfWriter()
    added_files = set()

    missing = []
    multi = []

    for d in drawings:
        hits = match_pdfs_for_drawing(pdf_names, d, order_no, machine_no)
        if not hits:
            missing.append(d)
            continue
        if len(hits) >= 2:
            multi.append((d, hits))

        for fn in hits:
            if fn in added_files:
                continue
            path = os.path.join(input_folder, fn)
            logging.info(f"[{d}] add: {fn}")
            with open(path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    writer.add_page(page)
            added_files.add(fn)

    with open(output_pdf_path, "wb") as out:
        writer.write(out)
    logging.info(f"Combined PDF saved to {output_pdf_path}")

    if missing:
        logging.warning(f"PDFが見つからない図番（{len(missing)}件）: " + ", ".join(missing[:50]) + (" ..." if len(missing) > 50 else ""))
    if multi:
        logging.warning(f"同一図番で複数PDFがヒット（{len(multi)}件）。必要なら後で優先規則を追加します。")
        for d, hits in multi[:20]:
            logging.warning(f"  - {d}: {hits}")

def combine_pdfs_pre_mode(config, input_folder, output_folder, order_no, machine_no):
    '''
    PREモード: 注文CSVなし。受注番号(必須)/機械番号(任意)でスコープ固定して、安定ソートで結合。
    '''
    os.makedirs(output_folder, exist_ok=True)
    output_pdf_path = os.path.join(output_folder, "combine_pre.pdf")

    pdf_names = list_pdfs(input_folder)
    if not pdf_names:
        logging.warning("input_folder にPDFが見つかりません。")
        return

    order_low = order_no.lower()
    machine_low = machine_no.lower() if machine_no else ""

    scoped = [p for p in pdf_names if order_low in p.lower()]
    if machine_low:
        scoped = [p for p in scoped if machine_low in p.lower()]

    scoped.sort(key=lambda x: x.lower())

    writer = PdfWriter()
    for fn in scoped:
        path = os.path.join(input_folder, fn)
        logging.info(f"add: {fn}")
        with open(path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                writer.add_page(page)

    with open(output_pdf_path, "wb") as out:
        writer.write(out)
    logging.info(f"Combined PDF saved to {output_pdf_path}")

def main():
    logging.basicConfig(level=logging.INFO)
    config, _ = load_config()

    input_folder = os.path.normpath(config["paths"]["input_folder"])
    output_folder = os.path.normpath(config["paths"]["output_folder"])

    mode = normalize(config.get("run", "mode", fallback="order")).lower()
    if mode not in ["order", "pre"]:
        logging.warning(f"run.mode が不正なので order として扱います: {mode}")
        mode = "order"

    order_no, machine_no = prompt_order_machine(config)
    logging.info(f"Mode={mode}, order_no={order_no}, machine_no={machine_no or '(none)'}")
    logging.info(f"Input folder: {input_folder}")
    logging.info(f"Output folder: {output_folder}")

    if mode == "order":
        combine_pdfs_order_mode(config, input_folder, output_folder, order_no, machine_no)
    else:
        combine_pdfs_pre_mode(config, input_folder, output_folder, order_no, machine_no)

if __name__ == "__main__":
    main()
