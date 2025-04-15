"""
txt2pdf_converter.py
功能：带智能图片压缩的目录结构保留PDF转换器
"""
import logging
import os
import re
import sys
import tempfile
from datetime import datetime
from fpdf import FPDF
from fontTools.ttLib import TTFont
from PIL import Image

# 配置参数
DEFAULT_FONT_SIZE = 12
MAX_PAGE_WIDTH = 190  # A4纸张宽度（单位：mm）
MAX_PAGE_HEIGHT = 270
SUPPORTED_IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
LOG_FILE = "conversion.log"


def setup_logging():
    """初始化日志记录"""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

    # 抑制第三方库日志
    logging.getLogger('fontTools').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('fpdf').setLevel(logging.WARNING)


def sanitize_filename(name):
    """生成安全文件名（保留中日文字符）"""
    clean_name = re.sub(r'[\\/*?:"<>|]', "-", name)
    clean_name = re.sub(r'[\t\n\r\f\v]+', '_', clean_name)
    return clean_name[:120]


class FileOutput:
    """虚拟输出用于计算换行"""

    def write(self, data):
        pass


class PDFConverter:
    def __init__(self, compress_ratio=0.6, jpeg_quality=85):
        self.pdf = FPDF()
        self.current_font = None
        self.available_fonts = []
        self.compress_ratio = compress_ratio  # 分辨率压缩比例
        self.jpeg_quality = jpeg_quality  # JPEG压缩质量
        self._init_pdf()

    def _init_pdf(self):
        """初始化PDF基础设置"""
        self.pdf.add_page()
        self.pdf.set_auto_page_break(True, margin=15)
        self.pdf.set_margins(10, 15, 10)
        self._load_fonts()

    def _load_fonts(self):
        """加载系统字体并排序"""
        font_paths = [
            ("NotoEmoji", "/System/Library/Fonts/NotoColorEmoji.ttf"),
            ("SegoeUIEmoji", "C:/Windows/Fonts/seguiemj.ttf"),
            ("Symbola", "/usr/share/fonts/truetype/symbola.ttf"),
            ("PingFang", os.path.expanduser("~/Library/Fonts/PingFang.ttc")),
            ("STHeiti", os.path.expanduser("~/Library/Fonts/华文黑体.ttf")),
            ("ArialUnicode", os.path.expanduser("~/Library/Fonts/Arial Unicode.ttf"))
        ]

        for name, path in font_paths:
            if os.path.exists(path):
                try:
                    self.pdf.add_font(name, "", path, uni=True)
                    self.available_fonts.append(name)
                except Exception as e:
                    logging.warning(f"字体加载失败：{name} - {str(e)}")

        if not self.available_fonts:
            self.pdf.add_font("Arial", "", "arial", uni=True)
            self.available_fonts.append("Arial")

        self.current_font = self.available_fonts[0]
        self.pdf.set_font(self.current_font, size=DEFAULT_FONT_SIZE)

    def _handle_unicode_char(self, char):
        """智能字体切换"""
        original_font = self.current_font
        for font in self.available_fonts:
            try:
                self.pdf.set_font(font)
                self.pdf.get_string_width(char)
                self.current_font = font
                return True
            except RuntimeError:
                continue
        self.pdf.set_font(original_font)
        return False

    def add_text(self, text):
        """精确换行文本处理"""
        self.pdf.start_section("")
        paragraphs = text.split('\n')

        for para in paragraphs:
            lines = self.pdf.multi_cell(
                w=MAX_PAGE_WIDTH - 20,
                h=10,
                txt=para,
                split_only=True,
                output=FileOutput()
            )

            for line in lines:
                current_line = []
                current_width = 0

                for char in line.strip('\r'):
                    if not self._handle_unicode_char(char):
                        char = '�'

                    char_width = self.pdf.get_string_width(char)

                    if current_width + char_width > MAX_PAGE_WIDTH - 20:
                        self.pdf.cell(current_width, 10, ''.join(current_line))
                        self.pdf.ln()
                        current_line = [char]
                        current_width = char_width
                    else:
                        current_line.append(char)
                        current_width += char_width

                if current_line:
                    self.pdf.cell(current_width, 10, ''.join(current_line))
                    self.pdf.ln()

            self.pdf.ln(3)

    def add_images(self, image_folder):
        """智能图片压缩处理"""
        images = sorted(
            [f for f in os.listdir(image_folder) if f.lower().endswith(SUPPORTED_IMAGE_EXT)],
            key=lambda x: os.path.splitext(x)[0]
        )

        if not images:
            return

        # 布局参数
        IMAGES_PER_PAGE = 6
        COLS = 2
        ROWS = 3
        MARGIN_X = 10
        MARGIN_Y = 15
        SPACING = 5

        # 计算单元格尺寸
        page_width_avail = MAX_PAGE_WIDTH - 2 * MARGIN_X
        cell_width = (page_width_avail - SPACING) / COLS
        page_height_avail = MAX_PAGE_HEIGHT - MARGIN_Y - 15
        cell_height = (page_height_avail - (ROWS - 1) * SPACING) / ROWS

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                for i, img_file in enumerate(images):
                    # 分页控制
                    if i % IMAGES_PER_PAGE == 0:
                        self.pdf.add_page()

                    # 计算位置
                    position = i % IMAGES_PER_PAGE
                    row = position // COLS
                    col = position % COLS
                    x = MARGIN_X + col * (cell_width + SPACING)
                    y = MARGIN_Y + row * (cell_height + SPACING)

                    # 图片压缩处理
                    img_path = os.path.join(image_folder, img_file)
                    temp_path = os.path.join(temp_dir, f"compressed_{i}.jpg")

                    with Image.open(img_path) as img:
                        # 格式转换
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert("RGB")

                        # 分辨率压缩
                        new_size = (
                            int(img.width * self.compress_ratio),
                            int(img.height * self.compress_ratio)
                        )
                        img = img.resize(new_size, Image.Resampling.LANCZOS)

                        # 保存压缩文件
                        img.save(
                            temp_path,
                            quality=self.jpeg_quality,
                            optimize=True,
                            subsampling=1  # 4:4:4色度抽样
                        )

                    # 计算缩放尺寸
                    with Image.open(temp_path) as compressed_img:
                        mm_width = compressed_img.width * 0.264583
                        mm_height = compressed_img.height * 0.264583

                        # 自适应缩放
                        width_ratio = cell_width / mm_width
                        height_ratio = cell_height / mm_height
                        scale_ratio = min(width_ratio, height_ratio)

                        # 应用缩放
                        scaled_width = mm_width * scale_ratio
                        scaled_height = mm_height * scale_ratio
                        x_offset = (cell_width - scaled_width) / 2
                        y_offset = (cell_height - scaled_height) / 2

                        self.pdf.image(
                            temp_path,
                            x=x + x_offset,
                            y=y + y_offset,
                            w=scaled_width,
                            h=scaled_height
                        )

            except Exception as e:
                logging.error(f"图片处理异常: {str(e)}")

    def save(self, output_path):
        self.pdf.output(output_path)


def convert_file(txt_path, output_dir, root_folder):
    """文件转换流程"""
    try:
        # 生成路径标识
        relative_path = os.path.relpath(os.path.dirname(txt_path), root_folder)
        path_parts = [sanitize_filename(p) for p in relative_path.split(os.sep) if p]

        # 文件名生成规则
        base_name = sanitize_filename(os.path.splitext(os.path.basename(txt_path))[0])
        if len(path_parts) >= 3:
            folder_name = "_".join(path_parts[-3:])
        else:
            folder_name = "_".join(path_parts) if path_parts else "root"

        output_name = f"xhs_{folder_name}_{base_name}.pdf"
        output_path = os.path.join(output_dir, output_name)

        # 避免重复
        if os.path.exists(output_path):
            timestamp = datetime.now().strftime("%H%M%S")
            output_name = f"{folder_name}_{base_name}_{timestamp}.pdf"
            output_path = os.path.join(output_dir, output_name)

        # 执行转换
        converter = PDFConverter(compress_ratio=0.6, jpeg_quality=85)
        with open(txt_path, "rb") as f:
            text = f.read().decode('utf-8', errors='replace')

        converter.add_text(text)
        converter.add_images(os.path.dirname(txt_path))
        converter.save(output_path)

        logging.info(f"转换成功：{output_name}")
        return True

    except Exception as e:
        logging.error(f"转换失败：{txt_path} - {str(e)}")
        return False


def main():
    setup_logging()

    root_folder = input("请输入根文件夹路径：").strip()
    if not os.path.isdir(root_folder):
        logging.error("错误：路径不存在或不是文件夹")
        return

    output_dir = os.path.join(root_folder, "PDF输出")
    os.makedirs(output_dir, exist_ok=True)

    processed = 0
    for root, _, files in os.walk(root_folder):
        if os.path.abspath(root).startswith(os.path.abspath(output_dir)):
            continue

        for file in files:
            if file.lower().endswith(".txt"):
                txt_path = os.path.join(root, file)
                if convert_file(txt_path, output_dir, root_folder):
                    processed += 1

    logging.info(f"处理完成！共转换 {processed} 个文件")


if __name__ == "__main__":
    main()