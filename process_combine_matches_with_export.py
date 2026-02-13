import pandas as pd
import os
import configparser
import logging

# INIコンフィグファイルを読み込む
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

def normalize_file_key(file_name: str) -> str:
    """
    Step4の File Name を集約用キーに正規化する。
    - パスが混ざっても basename 化
    - *_text.csv / .xlsx などを除去して「ベース名」に統一
    """
    s = str(file_name)
    s = os.path.basename(s)
    # まず拡張子を落とす
    base = os.path.splitext(s)[0]
    # *_text を落とす（TEXT CSV化で付く）
    if base.lower().endswith("_text"):
        base = base[:-5]
    return base

def process_and_combine_matches(input_path: str, output_path: str):
    """抽出結果Excelを処理し、ソートとグループ化を行い結果を出力する"""
    try:
        df = pd.read_excel(input_path)

        required_columns = {"File Name", "Match Type", "Match"}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"Input file must contain the following columns: {required_columns}")

        # 集約キーを追加（ここがCSV化対応の本体）
        df["File Key"] = df["File Name"].apply(normalize_file_key)

        # Match Type の順序を固定（Initial -> Extra -> No Match）
        type_order = pd.CategoricalDtype(
            categories=["Initial", "Extra", "No Match"],
            ordered=True
        )
        df["Match Type"] = df["Match Type"].astype(str)
        df["Match Type"] = df["Match Type"].where(df["Match Type"].isin(type_order.categories), "No Match")
        df["Match Type"] = df["Match Type"].astype(type_order)

        # ソート（File Key -> Match Type）
        df_sorted = df.sort_values(by=["File Key", "Match Type"], ascending=[True, True])

        # File Keyごとに Match を結合（重複は潰して順序維持）
        def join_unique(values):
            out = []
            seen = set()
            for v in values.astype(str):
                v = v.strip()
                if not v or v.lower() == "nan":
                    continue
                if v not in seen:
                    out.append(v)
                    seen.add(v)
            return " ".join(out)

        df_grouped = (
            df_sorted
            .groupby("File Key")["Match"]
            .apply(join_unique)
            .reset_index()
            .rename(columns={"File Key": "File Name"})
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_grouped.to_excel(output_path, index=False)
        logging.info(f"Processed data successfully saved to {output_path}")

    except Exception as e:
        logging.error(f"Failed to process the file {input_path}: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    input_file_path = os.path.join(config["paths"]["output_folder"], "extracted_misumi_types.xlsx")
    output_file_path = os.path.join(config["paths"]["output_folder"], "combine_misumi_types.xlsx")

    process_and_combine_matches(input_file_path, output_file_path)
