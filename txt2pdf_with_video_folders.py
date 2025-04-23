"""
txt2pdf_converter.py 最终优化版
包含所有字体处理改进和错误修复
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
from nbformat.v2 import new_output

# 配置参数
DEFAULT_FONT_SIZE = 12
CONTENT_FONT_SIZE = 14  # 增大内容字体大小
MAX_PAGE_WIDTH = 190
MAX_PAGE_HEIGHT = 270
SUPPORTED_IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
VIDEO_EXT = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.wav')
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
        """初始化PDF基础设置（移除初始空白页）"""
        self.pdf.set_auto_page_break(True, margin=15)
        self.pdf.set_margins(10, 15, 10)
        self._load_fonts()

    def _load_fonts(self):
        """加载系统字体（macOS优化版）"""
        font_paths = [
            ("NotoSansCJKsc", "/System/Library/Fonts/Supplemental/NotoSansCJKsc-Regular.ttf"),
            ("PingFang", "/System/Library/Fonts/PingFang.ttc"),
            ("Arial", "/Library/Fonts/Arial.ttf"),
            ("ArialUnicode", "/System/Library/Fonts/Arial Unicode.ttf"),
            ("Symbola", "/Library/Fonts/Symbola.ttf"),
            ("NotoColorEmoji", "/System/Library/Fonts/NotoColorEmoji.ttf"),
            ("NotoEmoji", "/System/Library/Fonts/NotoColorEmoji.ttf"),
            ("SegoeUIEmoji", "C:/Windows/Fonts/seguiemj.ttf"),
            ("Symbola", "/usr/share/fonts/truetype/symbola.ttf"),
            ("PingFang", os.path.expanduser("~/Library/Fonts/PingFang.ttc")),
            ("STHeiti", os.path.expanduser("~/Library/Fonts/华文黑体.ttf")),
            ("ArialUnicode", os.path.expanduser("~/Library/Fonts/Arial Unicode.ttf"))
        ]

        for font_name, font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    self.pdf.add_font(font_name, style="", fname=font_path, uni=True)
                    self.pdf.add_font(font_name, style="B", fname=font_path, uni=True)
                    self.available_fonts.append(font_name)
                except Exception as e:
                    logging.warning(f"字体加载失败：{font_name} - {str(e)}")
                    continue

        self.current_font = next(
            (f for f in ["NotoSansCJKsc", "PingFang", "Arial"] if f in self.available_fonts),
            self.available_fonts[0] if self.available_fonts else None
        )
        if self.current_font:
            self.pdf.set_font(self.current_font, size=DEFAULT_FONT_SIZE)

    def _handle_unicode_char(self, char):
        """智能字体切换（支持回退）"""
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
        self.pdf.set_font_size(CONTENT_FONT_SIZE)  # 使用更大的字体
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
        """高清封面处理"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                temp_path = tmp.name

                with Image.open(image_path) as img:
                    # 保持原始色彩模式
                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')

                    # 计算最佳缩放尺寸
                    original_width, original_height = img.size
                    target_width = int(MAX_PAGE_WIDTH * 0.9 * 3.78)  # 90%页面宽度（像素）
                    scaling_factor = min(target_width / original_width, 1.0)  # 不超过原尺寸
                    new_size = (
                        int(original_width * scaling_factor),
                        int(original_height * scaling_factor)
                    )

                    # 使用LANCZOS算法保持清晰度
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                    # 保存为无损PNG格式
                    img.save(temp_path, format='PNG', compress_level=0)

                # 添加到PDF（使用原始尺寸计算毫米单位）
                self.pdf.add_page()
                page_width = self.pdf.w - 20  # 留10mm边距
                x = 10 + (page_width - (new_size[0] / 3.78)) / 2  # 1英寸=25.4mm, 300dpi下1像素≈0.084mm
                self.pdf.image(temp_path, x=x, y=20, w=new_size[0] / 3.78)  # 精确像素转毫米

                # 移动封面到最后一页
                if len(self.pdf.pages) > 1:
                    cover_page = self.pdf.pages.pop()
                    self.pdf.pages.append(cover_page)

        except Exception as e:
            logging.error(f"封面处理异常: {str(e)}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def add_section_title(self, title):
        """章节标题样式"""
        self.pdf.set_font(self.current_font, 'B', 16)
        self.pdf.set_fill_color(240, 240, 240)
        self.pdf.cell(0, 12, title, ln=True, fill=True, border=0)
        self.pdf.ln(8)
        self.pdf.set_font_size(CONTENT_FONT_SIZE)  # 恢复内容字体大小

    def save(self, output_path):
        """最终保存方法"""
        self.pdf.output(output_path)


def convert_video_folder(folder_path, output_dir, root_folder):
    """改进的视频文件夹处理"""
    try:
        required_files = {
            'detail.txt': None,
            'audio.txt': None,
            'cover.jpg': None
        }

        for fname in required_files:
            fpath = os.path.join(folder_path, fname)
            if not os.path.exists(fpath):
                raise FileNotFoundError(f"缺失必要文件: {fname}")
            required_files[fname] = fpath

        converter = PDFConverter()
        converter.add_cover_image(required_files['cover.jpg'])
        converter.pdf.add_page()

        # 添加详情内容
        with open(required_files['detail.txt'], 'rb') as f:
            detail_text = f.read().decode('utf-8', errors='replace')
        converter.add_text(detail_text)

        # 添加视频文稿（使用更大字体）
        converter.pdf.add_page()
        converter.add_section_title("视频文稿")
        converter.pdf.set_font_size(CONTENT_FONT_SIZE)
        with open(required_files['audio.txt'], 'rb') as f:
            audio_text = f.read().decode('utf-8', errors='replace')
        converter.add_text(audio_text)

        # 生成输出路径
        relative_path = os.path.relpath(folder_path, root_folder)
        path_parts = [sanitize_filename(p) for p in relative_path.split(os.sep) if p]
        folder_name = "_".join(path_parts[-3:]) or "root"
        output_name = f"xhs_视频_{folder_name}.pdf"
# 改了这里
        new_output_dir_with_folder = output_dir + '/' + relative_path.split('/')[0]
        os.makedirs(new_output_dir_with_folder, exist_ok=True)
        output_path = os.path.join(new_output_dir_with_folder, output_name)

        if not os.path.exists(output_path):
            converter.save(output_path)
            logging.info(f"视频PDF转换成功：{output_name}")
            return True
        return False

    except Exception as e:
        logging.error(f"视频文件夹转换失败：{folder_path} - {str(e)}")
        return False


def convert_normal_txt(txt_path, output_dir, root_folder):
    """普通文本转换"""
    try:
        with open(txt_path, "rb") as f:
            text = f.read().decode('utf-8', errors='replace')

        converter = PDFConverter()
        converter.pdf.add_page()  # 添加内容页
        converter.add_text(text)

        # 生成输出路径
        txt_dir = os.path.dirname(txt_path)
        relative_path = os.path.relpath(txt_dir, root_folder)
        path_parts = [sanitize_filename(p) for p in relative_path.split(os.sep) if p]
        base_name = sanitize_filename(os.path.splitext(os.path.basename(txt_path))[0])
        folder_name = "_".join(path_parts[-3:]) or "root"
        output_name = f"xhs_{folder_name}_{base_name}.pdf"
        output_path = os.path.join(output_dir, output_name)

        if not os.path.exists(output_path):
            converter.save(output_path)
            logging.info(f"转换成功：{output_name}")
            return True
        return False

    except Exception as e:
        logging.error(f"转换失败：{txt_path} - {str(e)}")
        return False


def main():
    setup_logging()

    if len(sys.argv) < 2:
        root_folder = input("请输入根文件夹路径：").strip()
    else:
        root_folder = sys.argv[1]

    if not os.path.isdir(root_folder):
        logging.error("错误：路径不存在或不是文件夹")
        return

    # root_folder = '/Users/penghao/Documents/GitHub/Spider_XHS/datas/media_datas'
    output_dir_normal = os.path.join(root_folder, "小红书图文PDF输出")
    output_dir_video = os.path.join(root_folder, "小红书视频PDF输出")
    os.makedirs(output_dir_normal, exist_ok=True)
    os.makedirs(output_dir_video, exist_ok=True)

    processed_normal = 0
    processed_video = 0

    for root, dirs, files in os.walk(root_folder):
        if any(os.path.abspath(root).startswith(os.path.abspath(d)) for d in [output_dir_normal, output_dir_video]):
            continue

        # 优先处理视频文件夹
        if any(f.lower().endswith(VIDEO_EXT) for f in files):
            if convert_video_folder(root, output_dir_video, root_folder):
                processed_video += 1
    print(processed_video)

        # 处理普通文本文件
        # for file in files:
        #     if file.lower().endswith('.txt') and not file.lower().endswith('audio.txt'):
        #         if convert_normal_txt(os.path.join(root, file), output_dir_normal, root_folder):
        #             processed_normal += 1

    logging.info(f"\n转换统计：普通文件 {processed_normal} 个，视频文件夹 {processed_video} 个")


if __name__ == "__main__":
    main()