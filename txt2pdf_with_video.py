"""
txt2pdf_converter.py
最终版功能增强：
- 支持视频文件夹特殊处理
- 智能封面和文稿处理
- 双输出目录支持
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
MAX_PAGE_WIDTH = 190
MAX_PAGE_HEIGHT = 270
SUPPORTED_IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
VIDEO_EXT = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')
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
    def __init__(self, compress_ratio=0.8, jpeg_quality=95):
        self.pdf = FPDF()
        self.current_font = None
        self.available_fonts = []
        self.compress_ratio = compress_ratio
        self.jpeg_quality = jpeg_quality
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

    def add_cover_image(self, image_path):
        """添加封面页"""
        self.pdf.add_page()
        self.pdf.set_auto_page_break(False)
        margin = 15
        img_width = MAX_PAGE_WIDTH - 2 * margin
        img_height = MAX_PAGE_HEIGHT - 2 * margin - 10

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                temp_img_path = os.path.join(temp_dir, "cover.jpg")
                with Image.open(image_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    # 计算最佳缩放比例
                    width_ratio = img_width / img.width
                    height_ratio = img_height / img.height
                    scale_ratio = min(width_ratio, height_ratio)

                    new_size = (
                        int(img.width * scale_ratio),
                        int(img.height * scale_ratio)
                    )
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    img.save(temp_img_path, quality=95, optimize=True)

                # 计算居中位置
                x = margin + (img_width - new_size[0] * 0.264583) / 2
                y = margin + (img_height - new_size[1] * 0.264583) / 2

                self.pdf.image(
                    temp_img_path,
                    x=x,
                    y=y,
                    w=new_size[0] * 0.264583,
                    h=new_size[1] * 0.264583
                )

                # 添加封面文字
                self.pdf.set_font(self.current_font, 'B', 16)
                self.pdf.set_xy(margin, MAX_PAGE_HEIGHT - margin - 10)
                self.pdf.cell(0, 10, "封面", align='C')
            except Exception as e:
                logging.error(f"封面处理异常: {str(e)}")
                raise

        self.pdf.set_auto_page_break(True, margin=15)

    def add_section_title(self, title):
        """添加章节标题"""
        self.pdf.set_font(self.current_font, 'B', 16)
        self.pdf.cell(0, 10, title, ln=True)
        self.pdf.ln(5)
        self.pdf.set_font(self.current_font, size=DEFAULT_FONT_SIZE)

    def save(self, output_path):
        self.pdf.output(output_path)


def convert_video_folder(folder_path, output_dir, root_folder):
    """处理视频文件夹转换"""
    try:
        # 生成输出文件名
        relative_path = os.path.relpath(folder_path, root_folder)
        path_parts = [sanitize_filename(p) for p in relative_path.split(os.sep) if p]
        folder_name = "_".join(path_parts[-3:]) if len(path_parts) >= 3 else "_".join(path_parts) or "root"
        output_name = f"xhs_视频_{folder_name}.pdf"
        output_path = os.path.join(output_dir, output_name)

        if os.path.exists(output_path):
            logging.info(f"视频PDF已存在，跳过：{output_name}")
            return False

        # 检查必要文件
        detail_path = os.path.join(folder_path, 'detail.txt')
        audio_path = os.path.join(folder_path, 'audio.txt')
        cover_path = os.path.join(folder_path, 'cover.jpg')

        if not all(map(os.path.exists, [detail_path, audio_path, cover_path])):
            missing = [f for f in ['detail.txt', 'audio.txt', 'cover.jpg'] if
                       not os.path.exists(os.path.join(folder_path, f))]
            logging.warning(f"缺失必要文件: {', '.join(missing)}")
            return False

        # 初始化转换器
        converter = PDFConverter()

        # 添加封面
        converter.add_cover_image(cover_path)

        # 添加详细内容
        with open(detail_path, 'rb') as f:
            detail_text = f.read().decode('utf-8', errors='replace')
        converter.add_text(detail_text)

        # 添加视频文稿
        converter.pdf.add_page()
        converter.add_section_title("视频文稿")
        with open(audio_path, 'rb') as f:
            audio_text = f.read().decode('utf-8', errors='replace')
        converter.add_text(audio_text)

        converter.save(output_path)
        logging.info(f"视频PDF转换成功：{output_name}")
        return True

    except Exception as e:
        logging.error(f"视频文件夹转换失败：{folder_path} - {str(e)}")
        return False


def convert_normal_txt(txt_path, output_dir, root_folder):
    """处理普通文本文件转换"""
    try:
        txt_dir = os.path.dirname(txt_path)
        relative_path = os.path.relpath(txt_dir, root_folder)
        path_parts = [sanitize_filename(p) for p in relative_path.split(os.sep) if p]
        base_name = sanitize_filename(os.path.splitext(os.path.basename(txt_path))[0])
        folder_name = "_".join(path_parts[-3:]) if len(path_parts) >= 3 else "_".join(path_parts) or "root"

        output_name = f"xhs_{folder_name}_{base_name}.pdf"
        output_path = os.path.join(output_dir, output_name)

        if os.path.exists(output_path):
            logging.info(f"文件已存在，跳过转换：{output_name}")
            return False

        converter = PDFConverter()
        with open(txt_path, "rb") as f:
            text = f.read().decode('utf-8', errors='replace')

        converter.add_text(text)
        converter.add_images(txt_dir)
        converter.save(output_path)

        logging.info(f"转换成功：{output_name}")
        return True

    except Exception as e:
        logging.error(f"转换失败：{txt_path} - {str(e)}")
        return False


def main():
    setup_logging()

    # root_folder = input("请输入根文件夹路径：").strip()
    # if not os.path.isdir(root_folder):
    #     logging.error("错误：路径不存在或不是文件夹")
    #     return

    root_folder = '/Users/penghao/Documents/GitHub/Spider_XHS/datas/media_datas/健康/阿文就是Aya_5659a9f903eb841795e4fba9/8cm长的隧道，居然要干这么多活!_665ef0cd000000000e032f24'

    output_dir_normal = os.path.join(root_folder, "PDF输出")
    output_dir_video = os.path.join(root_folder, "输出视频pdf")
    os.makedirs(output_dir_normal, exist_ok=True)
    os.makedirs(output_dir_video, exist_ok=True)

    processed_normal = 0
    processed_video = 0
    missing_files = []

    for root, dirs, files in os.walk(root_folder):
        if any(os.path.abspath(root).startswith(os.path.abspath(d)) for d in [output_dir_normal, output_dir_video]):
            continue

        has_video = any(f.lower().endswith(VIDEO_EXT) for f in files)
        if has_video:
            required_files = {'detail.txt', 'audio.txt', 'cover.jpg'}
            present_files = set(files) & required_files
            if present_files == required_files:
                if convert_video_folder(root, output_dir_video, root_folder):
                    processed_video += 1
            else:
                missing = required_files - present_files
                missing_files.append((os.path.relpath(root, root_folder), missing))
        else:
            for file in files:
                if file.lower().endswith('.txt'):
                    if convert_normal_txt(os.path.join(root, file), output_dir_normal, root_folder):
                        processed_normal += 1

    # 输出统计信息
    logging.info(f"\n转换统计：")
    logging.info(f"普通文件转换成功: {processed_normal}")
    logging.info(f"视频文件转换成功: {processed_video}")

    if missing_files:
        logging.warning("\n缺失文件警告：")
        for path, missing in missing_files:
            logging.warning(f"路径: {path}")
            logging.warning(f"缺失文件: {', '.join(missing)}")
            logging.warning("------------------------")

    if processed_video + processed_normal == 0:
        logging.warning("没有找到任何可转换的文件")


if __name__ == "__main__":
    main()