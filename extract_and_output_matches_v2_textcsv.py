import pandas as pd
import re
import os
import configparser
import unicodedata

# INIコンフィグファイルを読み込む
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

def load_patterns(section_name: str):
    patterns = []
    if section_name in config:
        for key in sorted(config[section_name].keys()):
            patterns.append(config[section_name][key])
    return patterns

patterns = load_patterns("patterns")
extra_patterns = load_patterns("extra_patterns")

INPUT_FOLDER = config["paths"]["input_folder"]
OUTPUT_FOLDER = config["paths"]["output_folder"]

output_file = os.path.join(OUTPUT_FOLDER, "extracted_misumi_types.xlsx")

DEFAULT_EXCLUDE_LAYERS = {"201", "204"}
HYPHEN_TRANSLATION = str.maketrans({
    "－": "-", "ー": "-", "―": "-", "‐": "-", "‑": "-", "−": "-", "﹣": "-", "－": "-"
})

def parse_layer_set(value: str):
    if not value:
        return None
    parsed = {token.strip() for token in value.split(",") if token.strip()}
    return parsed or None

def get_layer_filters():
    # レイヤー設定をINI化（未指定時は既存の除外設定を維持）
    include_layers = parse_layer_set(config.get("filters", "include_layers", fallback=""))
    exclude_layers = parse_layer_set(config.get("filters", "exclude_layers", fallback=""))
    if exclude_layers is None:
        exclude_layers = set(DEFAULT_EXCLUDE_LAYERS)
    return include_layers, exclude_layers

INCLUDE_LAYERS, EXCLUDE_LAYERS = get_layer_filters()

def normalize_text(text: str):
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.translate(HYPHEN_TRANSLATION)
    normalized = normalized.replace("\u3000", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized

def clean_match_value(value: str):
    cleaned = re.sub(r"[^A-Z0-9-]", "", value.upper())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned

def load_prefixes_set():
    prefixes_path = config.get("paths", "prefixes_excel", fallback="").strip()
    if not prefixes_path:
        return set()
    if not os.path.exists(prefixes_path):
        print(f"[WARN] prefixes_excel not found: {prefixes_path}")
        return set()
    try:
        prefix_df = pd.read_excel(prefixes_path, dtype=str)
    except Exception as e:
        print(f"[ERROR] Failed to read prefixes excel '{prefixes_path}': {e}")
        return set()
    text_like_column = None
    for col in prefix_df.columns:
        series = prefix_df[col].dropna().astype(str).str.strip()
        if (series != "").any():
            text_like_column = col
            break
    if text_like_column is None:
        return set()
    prefixes = {
        normalize_text(v).upper()
        for v in prefix_df[text_like_column].dropna().astype(str)
        if normalize_text(v)
    }
    return prefixes

PREFIXES_SET = load_prefixes_set()

def is_target_layer(layer: str):
    if INCLUDE_LAYERS:
        return layer in INCLUDE_LAYERS
    return layer not in EXCLUDE_LAYERS

def collect_contexts_for_prefix(layer_df: pd.DataFrame):
    # 「型式」周辺の複数行連結を優先し、取りこぼし時のみ全行連結も探索
    contexts = []
    normalized_texts = [normalize_text(t) for t in layer_df["text"].tolist()]
    for i, line in enumerate(normalized_texts):
        if "型式" in line:
            contexts.append(" ".join(normalized_texts[i:i + 4]))
    if normalized_texts:
        contexts.append(" ".join(normalized_texts))
    return contexts

def extract_prefix_driven_match(df: pd.DataFrame):
    if not PREFIXES_SET:
        return None, ""
    sorted_prefixes = sorted(PREFIXES_SET, key=len, reverse=True)
    for layer, layer_df in df.groupby("layer", sort=False):
        for context in collect_contexts_for_prefix(layer_df):
            upper_context = context.upper()
            compact_context = re.sub(r"\s+", "", upper_context)
            for prefix in sorted_prefixes:
                # 可変長プレフィックスは最長一致優先で抽出
                m = re.search(rf"{re.escape(prefix)}([A-Z0-9-]{{3,}})", compact_context)
                if m:
                    candidate = clean_match_value(prefix + m.group(1))
                    if candidate:
                        return (layer, candidate, "Initial", "prefix", context[:200]), context
    return None, ""

def extract_matches_from_text_csv(file_path: str):
    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig", dtype=str)
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding="utf-8", dtype=str)

    if not {"layer", "text"}.issubset(df.columns):
        return []

    df["layer"] = df["layer"].fillna("").astype(str).str.strip()
    df["text"] = df["text"].fillna("").astype(str)

    df = df[df["layer"].apply(is_target_layer)]

    matches = []
    initial_match = None
    initial_layer = None
    initial_method = ""
    raw_context = ""

    prefix_result, prefix_context = extract_prefix_driven_match(df)
    if prefix_result:
        initial_layer, initial_match, match_type, initial_method, raw_context = prefix_result
        matches.append((os.path.basename(file_path), initial_layer, initial_match, match_type, initial_method, raw_context))

    if initial_match is None:
        for _, row in df.iterrows():
            layer = row["layer"]
            text = row["text"]
            normalized_text = normalize_text(text)
            for pattern in patterns:
                m = re.search(pattern, normalized_text)
                if m:
                    initial_match = m.group(0)
                    initial_layer = layer
                    initial_method = "pattern"
                    raw_context = normalized_text[:200]
                    matches.append((os.path.basename(file_path), layer, initial_match, "Initial", initial_method, raw_context))
                    break
            if initial_match:
                break

    if initial_layer is not None and extra_patterns:
        df_layer = df[df["layer"] == initial_layer]
        for _, row in df_layer.iterrows():
            text = normalize_text(row["text"])
            for ep in extra_patterns:
                m2 = re.search(ep, text)
                if m2:
                    matches.append((os.path.basename(file_path), initial_layer, m2.group(0), "Extra", "pattern", text[:200]))

    if not matches:
        matches.append((os.path.basename(file_path), "", "No Match", "No Match", "", ""))

    return matches

def main():
    all_matches = []

    for filename in os.listdir(INPUT_FOLDER):
        if filename.lower().endswith("_text.csv"):
            file_path = os.path.join(INPUT_FOLDER, filename)
            try:
                all_matches.extend(extract_matches_from_text_csv(file_path))
            except Exception as e:
                print(f"[ERROR] Failed to process {file_path}: {e}")
                all_matches.append((filename, "", "No Match", "Error", "", str(e)))

    out_df = pd.DataFrame(all_matches, columns=["File Name", "Layer", "Match", "Match Type", "Method", "RawContext"])
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    out_df.to_excel(output_file, index=False)

if __name__ == "__main__":
    main()
