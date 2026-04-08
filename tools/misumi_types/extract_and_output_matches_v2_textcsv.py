import pandas as pd
import re
import os
import configparser

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

EXCLUDE_LAYERS = {"201", "204"}

def extract_matches_from_text_csv(file_path: str):
    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig", dtype=str)
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding="utf-8", dtype=str)

    if not {"layer", "text"}.issubset(df.columns):
        return []

    df["layer"] = df["layer"].fillna("").astype(str).str.strip()
    df["text"] = df["text"].fillna("").astype(str)

    df = df[~df["layer"].isin(EXCLUDE_LAYERS)]

    matches = []
    initial_match = None
    initial_layer = None

    for _, row in df.iterrows():
        layer = row["layer"]
        text = row["text"]
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                initial_match = m.group(0)
                initial_layer = layer
                matches.append((os.path.basename(file_path), layer, initial_match, "Initial"))
                break
        if initial_match:
            break

    if initial_layer is not None and extra_patterns:
        df_layer = df[df["layer"] == initial_layer]
        for _, row in df_layer.iterrows():
            text = row["text"]
            for ep in extra_patterns:
                m2 = re.search(ep, text)
                if m2:
                    matches.append((os.path.basename(file_path), initial_layer, m2.group(0), "Extra"))

    if not matches:
        matches.append((os.path.basename(file_path), "", "No Match", "No Match"))

    return matches

def main():
    all_matches = []

    for filename in os.listdir(INPUT_FOLDER):
        if filename.lower().endswith("_text.csv"):
            file_path = os.path.join(INPUT_FOLDER, filename)
            all_matches.extend(extract_matches_from_text_csv(file_path))

    out_df = pd.DataFrame(all_matches, columns=["File Name", "Layer", "Match", "Match Type"])
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    out_df.to_excel(output_file, index=False)

if __name__ == "__main__":
    main()
