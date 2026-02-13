import ezdxf
import pandas as pd
import os
import logging
import configparser

# INIコンフィグファイルを読み込む
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

def extract_text_entities_to_csv(dxf_file_path: str, csv_output_path: str):
    """DXFファイルから TEXT エンティティの layer/text を抽出しCSVに保存する"""
    try:
        doc = ezdxf.readfile(dxf_file_path)
        logging.info(f"Successfully read DXF file: {dxf_file_path}")
    except IOError:
        logging.error(f"Failed to read DXF file: {dxf_file_path}")
        return
    except ezdxf.DXFStructureError:
        logging.error(f"Invalid DXF file: {dxf_file_path}")
        return
    except Exception as e:
        logging.error(f"Unexpected error reading DXF file: {dxf_file_path}. Error: {e}")
        return

    try:
        msp = doc.modelspace()
        rows = []
        for ent in msp.query("TEXT"):
            try:
                rows.append({
                    "layer": ent.dxf.layer,
                    "text": ent.dxf.text
                })
            except Exception:
                continue

        df = pd.DataFrame(rows, columns=["layer", "text"])
        df.to_csv(csv_output_path, index=False, encoding="utf-8-sig")
        logging.info(f"Successfully wrote TEXT CSV: {csv_output_path}")
    except Exception as e:
        logging.error(f"Failed to write TEXT CSV: {csv_output_path}. Error: {e}")

def process_all_dxf_files(folder_path: str):
    """指定フォルダ内のすべてのDXFファイルから TEXT を抽出し *_text.csv を作成する"""
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".dxf"):
            dxf_file_path = os.path.join(folder_path, filename)
            base_name = os.path.splitext(dxf_file_path)[0]
            csv_output_path = base_name + "_text.csv"
            logging.info(f"Processing DXF file (TEXT only): {dxf_file_path}")
            extract_text_entities_to_csv(dxf_file_path, csv_output_path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    folder_path = config["paths"]["input_folder"]
    process_all_dxf_files(folder_path)
