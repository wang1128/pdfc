import os
import re
from fpdf import FPDF

# 字体处理部分保持不变
USER_FONT_DIR = os.path.expanduser("~/fpdf_fonts")
os.makedirs(USER_FONT_DIR, exist_ok=True)
FPDF_FONT_DIR = USER_FONT_DIR


def sanitize_filename(name):
    """生成安全文件名，处理特殊字符和长度"""
    # 替换非法字符
    clean_name = re.sub(r'[\\/*?:"<>|]', "-", name)
    # 替换连续空格为单个下划线
    clean_name = re.sub(r'\s+', '_', clean_name)
    # 保留前40个字符
    return clean_name[:40]


def convert_txt_to_pdf(txt_path, pdf_path):
    """文本转PDF核心函数（保持原功能）"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # 字体选择逻辑保持不变
    font_path = os.path.expanduser("~/Library/Fonts/")
    supported_fonts = [
        ("PingFang", f"{font_path}PingFang.ttc"),
        ("ArialUnicode", f"{font_path}Arial Unicode.ttf"),
        ("STHeiti", f"{font_path}华文黑体.ttf")
    ]

    selected_font = None
    for name, path in supported_fonts:
        if os.path.exists(path):
            try:
                pdf.add_font(name, "", path, uni=True)
                selected_font = name
                break
            except:
                continue

    if not selected_font:
        pdf.add_font("Arial", "", "arial", uni=True)
        selected_font = "Arial"

    pdf.set_font(selected_font, size=12)

    # 编码检测逻辑
    encodings = ['utf-8', 'gb18030', 'big5', 'latin-1']
    with open(txt_path, "rb") as f:
        content = f.read()
        for encoding in encodings:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = content.decode('utf-8', errors='replace')

    pdf.multi_cell(0, 10, txt=text, max_line_height=pdf.font_size * 1.5)
    pdf.output(pdf_path)


def main():
    # 获取用户输入路径
    root_folder = input("请输入根文件夹路径：").strip()

    if not os.path.isdir(root_folder):
        print("错误：路径不存在或不是文件夹")
        return

    # 创建PDF输出目录
    output_dir = os.path.join(root_folder, "PDF输出")
    os.makedirs(output_dir, exist_ok=True)

    # 使用字典跟踪父文件夹的文件计数
    folder_counter = {}

    # 遍历所有子文件夹
    for root, dirs, files in os.walk(root_folder):
        # 跳过输出目录
        if os.path.abspath(root).startswith(os.path.abspath(output_dir)):
            continue

        for file in files:
            if file.lower().endswith(".txt"):
                txt_path = os.path.join(root, file)

                # 获取父文件夹名称
                parent_folder = os.path.basename(root)
                # 生成安全基础名称
                base_name = sanitize_filename(parent_folder)

                # 更新计数器
                if base_name not in folder_counter:
                    folder_counter[base_name] = 1
                else:
                    folder_counter[base_name] += 1

                # 生成最终文件名
                if folder_counter[base_name] == 1:
                    pdf_name = f"{base_name}.pdf"
                else:
                    pdf_name = f"{base_name}_{folder_counter[base_name] - 1}.pdf"

                # 完整输出路径
                pdf_path = os.path.join(output_dir, pdf_name)

                try:
                    convert_txt_to_pdf(txt_path, pdf_path)
                    rel_path = os.path.relpath(txt_path, root_folder)
                    print(f"✅ 转换成功：{rel_path} → {pdf_name}")
                except Exception as e:
                    rel_path = os.path.relpath(txt_path, root_folder)
                    print(f"❌ 转换失败：{rel_path} - {str(e)}")


if __name__ == "__main__":
    main()