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
        raise KeyError("Missing [scripts] section in config.ini")
    items = []
    for k, v in config["scripts"].items():
        kk = k.strip().lower()
        if kk.startswith("script_"):
            try:
                idx = int(kk.split("_", 1)[1])
            except Exception:
                continue
            items.append((idx, v.strip()))
    items.sort(key=lambda x: x[0])
    return [v for _, v in items]

def resolve_script_path(script_folder: str, script_name: str):
    """Resolve script path with small fallbacks to absorb naming drift."""
    candidates = [script_name]

    # If config points to *_patched2.py but only the original exists.
    if script_name.endswith("_patched2.py"):
        candidates.append(script_name.replace("_patched2.py", ".py"))

    # If config points to .py but a patched file exists in the folder, prefer it.
    if script_name.endswith(".py") and not script_name.endswith("_patched2.py"):
        candidates.insert(0, script_name.replace(".py", "_patched2.py"))

    for name in candidates:
        p = os.path.join(script_folder, name)
        if os.path.exists(p):
            return p

    return os.path.join(script_folder, script_name)

def main():
    logging.basicConfig(level=logging.INFO)

    config, here = load_config()

    # IMPORTANT: Force script_folder to the same directory as this runner
    # to avoid mixing misumi_types vs misumi_types_2 paths.
    script_folder = here
    logging.info(f"Using script_folder (forced): {script_folder}")

    scripts = load_scripts_to_execute(config)

    for script_name in scripts:
        script_path = resolve_script_path(script_folder, script_name)
        execute_script(script_path)

if __name__ == "__main__":
    main()
