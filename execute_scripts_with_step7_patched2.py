import subprocess
import os
import logging
import configparser
import sys
from datetime import datetime

def load_config():
    config = configparser.ConfigParser()
    here = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(here, "config.ini")
    config.read(config_path, encoding="utf-8")
    return config, here

def execute_script(script_path: str):
    start_time = datetime.now()
    normalized_path = os.path.normpath(script_path)
    logging.info(f"Starting execution of {normalized_path} at {start_time}")
    try:
        subprocess.run([sys.executable, normalized_path], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing {normalized_path}: {e}")
        raise
    finally:
        end_time = datetime.now()
        logging.info(f"Finished execution of {normalized_path} at {end_time}")
        logging.info(f"Execution time: {end_time - start_time}")

def load_scripts_to_execute(config):
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

    config, here = load_config()

    # config が古い/移動した場合でも動くように、実行スクリプトのフォルダを優先
    script_folder = os.path.normpath(config.get("paths", "script_folder", fallback=here))
    if not os.path.isdir(script_folder):
        script_folder = here

    scripts_to_execute = load_scripts_to_execute(config)

    for script in scripts_to_execute:
        script_path = os.path.join(script_folder, script)
        execute_script(script_path)
