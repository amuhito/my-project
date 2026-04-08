import os
from PyPDF2 import PdfReader, PdfWriter
import configparser
import logging

# INIコンフィグファイルを読み込む
config = configparser.ConfigParser()
config.read("config.ini")

# フォルダパスをコンフィグから取得
folder_path = config['paths']['input_folder']
output_pdf_path = os.path.join(config['paths']['output_folder'], 'combine_misumi.pdf')

# ログ設定
logging.basicConfig(level=logging.INFO)

# PDFファイル結合用のライターを作成
pdf_writer = PdfWriter()

# フォルダ内のすべてのPDFファイルを走査
for item in os.listdir(folder_path):
    if item.endswith('.pdf'):
        file_path = os.path.join(folder_path, item)
        if os.path.isfile(file_path):
            try:
                logging.info(f"Processing file: {file_path}")
                with open(file_path, 'rb') as file:
                    pdf_reader = PdfReader(file)
                    # 各ページを結合する
                    for page_num in range(len(pdf_reader.pages)):
                        logging.info(f"Adding page {page_num + 1} of {file_path}")
                        page = pdf_reader.pages[page_num]
                        pdf_writer.add_page(page)
            except Exception as e:
                logging.error(f"Failed to process {file_path}: {e}")
                continue

# 結合したPDFファイルを保存
try:
    with open(output_pdf_path, 'wb') as out:
        pdf_writer.write(out)
    logging.info(f"Combined PDF saved to {output_pdf_path}")
except Exception as e:
    logging.error(f"Failed to save the combined PDF: {e}")
