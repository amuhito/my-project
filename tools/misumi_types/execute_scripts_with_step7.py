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
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config.ini not found: {config_path}")
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


def main():
    logging.basicConfig(filename="script_execution.log", level=logging.INFO)

    config, here = load_config()

    script_folder = os.path.normpath(config.get("paths", "script_folder", fallback=here))
    if not os.path.isdir(script_folder):
        logging.warning(f"script_folder not found; fallback to runner directory: {script_folder}")
        script_folder = here

    for script in load_scripts_to_execute(config):
        execute_script(os.path.join(script_folder, script))


if __name__ == "__main__":
    main()
