import os
import shutil
import logging
import configparser

# INIコンフィグファイルを読み込む
config = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')

def clean_input_folder(input_folder):
    """input フォルダ内のすべてのファイルを削除"""
    for filename in os.listdir(input_folder):
        file_path = os.path.join(input_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logging.error(f"Failed to delete {file_path}. Reason: {e}")
    logging.info(f"Cleaned the input folder: {input_folder}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    input_folder = os.path.normpath(config['paths']['input_folder'])
    clean_input_folder(input_folder)
