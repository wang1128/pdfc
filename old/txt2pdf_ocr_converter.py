"""
txt2pdf_ocr_final.py
功能：带OCR识别的高级文本转PDF工具
"""
import logging
import os
import re
import sys
from PIL import Image
import pytesseract
from fpdf import FPDF

# 全局配置
DEFAULT_FONT_SIZE = 12
MAX_PAGE_WIDTH = 190  # 单位：mm
LOG_FILE = "pdf_conversion.log"
SUPPORTED_IMG_EXTS = ('.png', '.jpg', '.jpeg')


def setup_logging():
    """配置静默日志系统"""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        force=True
    )
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('fontTools').setLevel(logging.WARNING)


def sanitize_filename(name):
    """生成安全文件名"""
    return re.sub(r'[\\/*?:"<>|]', "-", name.strip())[:100]


class AdvancedPDFConverter:
    def __init__(self):
        self.pdf = FPDF()
        self.fonts_loaded = []
        self._initialize_document()

    def _initialize_document(self):
        """初始化PDF文档设置"""
        self.pdf.add_page()
        self.pdf.set_auto_page_break(True, margin=15)
        self.pdf.set_margins(10, 15, 10)
        self._load_custom_fonts()
        self._set_default_font()

    def _load_custom_fonts(self):
        """加载多语言支持字体"""
        font_configs = [
            {
                "name": "NotoSerifSC",
                "path": "/System/Library/Fonts/NotoSerifCJKsc-Regular.otf",
                "style": ""
            },
            {
                "name": "PingFang",
                "path": "/System/Library/Fonts/PingFang.ttc",
                "style": "",
                "index": 0
            },
            {
                "name": "ArialUnicode",
                "path": "/usr/share/fonts/truetype/arial-unicode-ms.ttf",
                "style": ""
            }
        ]

        for config in font_configs:
            if os.path.exists(config["path"]):
                try:
                    self.pdf.add_font(
                        family=config["name"],
                        style=config["style"],
                        fname=config["path"],
                        uni=True
                    )
                    self.fonts_loaded.append(config["name"])
                except Exception as e:
                    logging.warning(f"字体加载失败 {config['name']}: {str(e)}")

    def _set_default_font(self):
        """设置回退字体"""
        if self.fonts_loaded:
            self.pdf.set_font(self.fonts_loaded[0], size=DEFAULT_FONT_SIZE)
        else:
            self.pdf.set_font("helvetica", size=DEFAULT_FONT_SIZE)

    def _process_images(self, folder_path):
        """处理图片OCR识别"""
        ocr_results = []
        for file in sorted(os.listdir(folder_path)):
            if file.lower().endswith(SUPPORTED_IMG_EXTS):
                img_path = os.path.join(folder_path, file)
                try:
                    text = pytesseract.image_to_string(
                        Image.open(img_path),
                        lang='chi_sim+eng'
                    )
                    ocr_results.append(f"\n[图片内容识别：{file}]\n{text.strip()}\n")
                except Exception as e:
                    logging.error(f"OCR处理失败 {file}: {str(e)}")
        return "\n".join(ocr_results)

    def _smart_line_break(self, text):
        """智能文本布局引擎"""
        content = text.replace('\r', '')  # 过滤回车符
        paragraphs = content.split('\n')

        for para in paragraphs:
            # 预计算自动换行
            lines = self.pdf.multi_cell(
                w=MAX_PAGE_WIDTH - 20,
                h=10,
                text=para,
                dry_run=True,
                output="LINES"
            )

            # 逐行写入
            for line in lines:
                self.pdf.cell(0, 10, line, new_x="LMARGIN", new_y="NEXT")
            self.pdf.ln(3)  # 段落间距

    def generate_pdf(self, text_content, image_folder, output_path):
        """生成PDF主流程"""
        # 添加OCR文本
        ocr_text = self._process_images(image_folder)
        full_content = f"{text_content}\n{ocr_text}"

        # 排版内容
        self._smart_line_break(full_content)

        # 输出文件
        self.pdf.output(output_path)
        logging.info(f"PDF生成成功：{output_path}")


def process_files(root_folder, output_dir):
    """深度递归文件处理器"""
    processed_count = 0
    error_count = 0

    # 使用广度优先遍历提高深层目录处理效率
    for root, dirs, files in os.walk(root_folder, topdown=True):
        # 跳过输出目录
        if os.path.abspath(root).startswith(os.path.abspath(output_dir)):
            continue

        # 处理当前目录文件
        for filename in files:
            if filename.lower().endswith('.txt'):
                txt_path = os.path.join(root, filename)

                try:
                    # 生成安全输出路径（保留完整目录结构）
                    rel_path = os.path.relpath(root, root_folder)
                    safe_path = "_".join([
                        sanitize_filename(p)
                        for p in rel_path.split(os.sep)
                        if p not in ('', '.')
                    ])
                    safe_filename = sanitize_filename(os.path.splitext(filename)[0])
                    output_name = f"{safe_path}_{safe_filename}.pdf" if safe_path else f"{safe_filename}.pdf"
                    output_path = os.path.join(output_dir, output_name)

                    # 避免文件覆盖
                    if os.path.exists(output_path):
                        version = 1
                        while os.path.exists(f"{output_path}.{version}"):
                            version += 1
                        output_path = f"{output_path}.{version}"

                    # 执行转换
                    with open(txt_path, 'rb') as f:
                        text_content = f.read().decode('utf-8', errors='replace')

                    converter = AdvancedPDFConverter()
                    converter.generate_pdf(text_content, root, output_path)
                    processed_count += 1

                except Exception as e:
                    error_count += 1
                    logging.error(f"处理失败 {txt_path} | 错误类型：{type(e).__name__} | 详细信息：{str(e)}")
                    continue

    # 生成总结报告
    logging.info(f"处理完成 | 成功：{processed_count} | 失败：{error_count}")
    print(f"\n处理结果：")
    print(f"✅ 成功转换文件：{processed_count}")
    print(f"❌ 失败文件：{error_count}")
    print(f"📁 输出目录：{os.path.abspath(output_dir)}")
    print(f"📋 详细日志：{os.path.abspath(LOG_FILE)}")

    return processed_count


if __name__ == "__main__":
    setup_logging()

    # 检查Tesseract安装
    if not pytesseract.get_tesseract_version():
        print("错误：需要安装Tesseract OCR引擎")
        print("Windows用户：从 https://github.com/UB-Mannheim/tesseract/wiki 下载安装")
        print("Mac用户：brew install tesseract")
        print("Linux用户：sudo apt install tesseract-ocr-all")
        sys.exit(1)

    # 获取输入路径
    input_folder = input("请输入要处理的根文件夹路径：").strip()
    if not os.path.isdir(input_folder):
        print("错误：输入的路径不存在或不是文件夹")
        sys.exit(2)

    # 准备输出目录
    output_folder = os.path.join(input_folder, "PDF输出")
    os.makedirs(output_folder, exist_ok=True)

    # 执行转换
    total_processed = process_files(input_folder, output_folder)
    print(f"\n转换完成！共处理 {total_processed} 个文件")
    print(f"日志文件位置：{os.path.abspath(LOG_FILE)}")
    print(f"输出目录：{os.path.abspath(output_folder)}")