import os
from fpdf import FPDF


def txt_to_pdf(txt_file_path, pdf_file_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    try:
        with open(txt_file_path, 'r', encoding='utf-8') as file:
            for line in file:
                pdf.cell(200, 10, txt=line.strip(), ln=True, align='L')
        pdf.output(pdf_file_path)
        print(f"成功将 {txt_file_path} 转换为 {pdf_file_path}")
    except Exception as e:
        print(f"转换 {txt_file_path} 时出错: {e}")


def convert_folder(folder_name):
    if not os.path.exists(folder_name):
        print(f"文件夹 {folder_name} 不存在。")
        return

    for root, dirs, files in os.walk(folder_name):
        for file in files:
            if file.endswith('.txt'):
                txt_file_path = os.path.join(root, file)
                pdf_file_name = os.path.splitext(file)[0] + '.pdf'
                pdf_file_path = os.path.join(root, pdf_file_name)
                txt_to_pdf(txt_file_path, pdf_file_path)


if __name__ == "__main__":
    folder_name = input("请输入文件夹名称: ")
    convert_folder(folder_name)
