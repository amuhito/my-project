import subprocess
import os
import logging
import configparser
from datetime import datetime

# INIコンフィグファイルを読み込む
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

def execute_script(script_path: str):
    start_time = datetime.now()
    normalized_path = os.path.normpath(script_path)
    logging.info(f"Starting execution of {normalized_path} at {start_time}")
    try:
        subprocess.run(["python", normalized_path], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing {normalized_path}: {e}")
        raise
    finally:
        end_time = datetime.now()
        logging.info(f"Finished execution of {normalized_path} at {end_time}")
        logging.info(f"Execution time: {end_time - start_time}")

def load_scripts_to_execute():
    # [scripts] の script_1, script_2, ... を番号順に自動収集する。
    # 既存のscript_1〜6に加えて、script_7 以降も追加できる。
    if "scripts" not in config:
        raise KeyError("config.ini に [scripts] セクションがありません。")
    items = []
    for k, v in config["scripts"].items():
        kk = k.strip().lower()
        if kk.startswith("script_"):
            try:
                n = int(kk.split("_", 1)[1])
            except Exception:
                continue
            items.append((n, v.strip()))
    items.sort(key=lambda x: x[0])
    return [v for _, v in items]

if __name__ == "__main__":
    logging.basicConfig(filename="script_execution.log", level=logging.INFO)

    script_folder = os.path.normpath(config["paths"]["script_folder"])
    scripts_to_execute = load_scripts_to_execute()

    for script in scripts_to_execute:
        script_path = os.path.join(script_folder, script)
        execute_script(script_path)

        # copy_files_to_input.py の後に一時停止（手作業のコピー完了待ち）
        if "scripts" in config and script == config["scripts"].get("script_2", "").strip():
            input("copy_files_to_input.py の操作が完了したら Enter を押してください（次へ進みます）...")
