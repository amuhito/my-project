import os
import subprocess
import logging
import configparser
import time

# INIコンフィグファイルを読み込む
config = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')

def open_explorer(path):
    """指定されたパスをエクスプローラーで開き、小さく表示"""
    try:
        # エクスプローラーを開く
        subprocess.run(["explorer", os.path.normpath(path)])
        logging.info(f"{path} をエクスプローラーで開きました。")
        
        # 少し待ってからPowerShellでウィンドウを調整
        time.sleep(1)  # ウィンドウが開かれるまで少し待機
        subprocess.run([
            "powershell",
            "-ExecutionPolicy", "Bypass",
            "-File", "resize_explorer.ps1"
        ])
        logging.info("ウィンドウのサイズを小さく設定しました。")
    except Exception as e:
        logging.error(f"{path} をエクスプローラーで開けませんでした。理由: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # ソースフォルダとインプットフォルダのパスを取得
    source_folder = os.path.normpath(config['paths']['source_folder'])
    input_folder = os.path.normpath(config['paths']['input_folder'])
    
    # エクスプローラーでソースフォルダとインプットフォルダを開く
    logging.info("ソースフォルダとインプットフォルダをエクスプローラーで開きます。")
    open_explorer(source_folder)
    open_explorer(input_folder)
    
    # ユーザーに検索とコピーを促す
    print(f"ソースフォルダでファイルを検索してください: {source_folder}")
    print(f"その後、選択したファイルをインプットフォルダにコピーしてください: {input_folder}")
    
    # 作業が完了するまで一時停止
    input("ファイルのコピーが完了したら、Enterキーを押して次の処理に進んでください...")

    # 作業完了後に続けて処理を行う
    print("処理を続行します...")
    # ここに続けて行いたい処理を記述
    # 例: 他のスクリプトを実行するなど
    # subprocess.run(["python", "next_script.py"])
