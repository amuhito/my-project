import os
import subprocess
import logging
import configparser
import time

def load_config():
    config = configparser.ConfigParser()
    here = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(here, "config.ini")
    config.read(config_path, encoding="utf-8")
    return config, here

def open_explorer(path, ps1_path):
    """指定されたパスをエクスプローラーで開き、小さく表示"""
    try:
        subprocess.run(["explorer", os.path.normpath(path)], check=False)
        logging.info(f"{path} をエクスプローラーで開きました。")
        time.sleep(1)
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps1_path], check=False)
        logging.info("ウィンドウのサイズを小さく設定しました。")
    except Exception as e:
        logging.error(f"{path} をエクスプローラーで開けませんでした。理由: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config, here = load_config()

    source_folder = os.path.normpath(config["paths"]["source_folder"])
    input_folder = os.path.normpath(config["paths"]["input_folder"])
    ps1_path = os.path.join(here, "resize_explorer.ps1")

    logging.info("ソースフォルダとインプットフォルダをエクスプローラーで開きます。")
    open_explorer(source_folder, ps1_path)
    open_explorer(input_folder, ps1_path)

    print(f"ソースフォルダでファイルを検索してください: {source_folder}")
    print(f"その後、選択したファイルをインプットフォルダにコピーしてください: {input_folder}")

    input("ファイルのコピーが完了したら、Enterキーを押して次の処理に進んでください...")

    print("処理を続行します...")
