"""
txt2pdf_converter.py
最终版功能：
- 保留目录结构
- 智能字体处理
- 每页4张图片布局（2x2）
- 增强图片清晰度
- 视频文件检测
- 防重复转换
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
MAX_PAGE_WIDTH = 190  # A4纸张宽度（mm）
MAX_PAGE_HEIGHT = 270
SUPPORTED_IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
VIDEO_EXT = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.wav')
LOG_FILE = "conversion.log"

import os
import glob
global user_id_dict  # 声明为全局字典
user_id_dict = {}

def process_folder(folder_path):
    global user_id_dict  # 必须声明为global
    stats = {
        'total_files': 0,
        'total_urls': 0,
        'success': 0,
        'failed': 0,
        'duplicates': 0
    }

    # 获取所有txt文件路径
    txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
    stats['total_files'] = len(txt_files)

    for file_path in txt_files:
        # 提取赛道名称（不带扩展名）
        sector_name = os.path.splitext(os.path.basename(file_path))[0]

        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        for url in urls:
            stats['total_urls'] += 1
            profile_pos = url.find('/user/profile/')

            if profile_pos == -1:  # 无效URL格式
                stats['failed'] += 1
                continue

            # 计算ID起始位置
            id_start = profile_pos + len('/user/profile/')
            query_start = url.find('?', id_start)

            # 提取用户ID
            user_id = url[id_start:query_start] if query_start != -1 else url[id_start:]

            if not user_id:  # ID为空的情况
                stats['failed'] += 1
                continue

            # 更新字典和统计
            if user_id in user_id_dict:
                stats['duplicates'] += 1
            else:
                stats['success'] += 1

            user_id_dict[user_id] = sector_name  # 始终更新最新赛道名称

    # 打印统计报告
    print(f"\n{' 统计报告 ':=^40}")
    print(f"处理文件夹: {folder_path}")
    print(f"分析文件总数: {stats['total_files']} 个")
    print(f"有效URL数量: {stats['success']} 条")
    print(f"无效URL数量: {stats['failed']} 条")
    print(f"重复ID数量: {stats['duplicates']} 次")
    print(f"唯一ID总数: {len(user_id_dict)} 个")
    print("=" * 40 + "\n")

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
    def __init__(self, compress_ratio=0.8, jpeg_quality=95):  # 调整压缩参数
        self.pdf = FPDF()
        self.current_font = None
        self.available_fonts = []
        self.compress_ratio = compress_ratio  # 提高压缩比例
        self.jpeg_quality = jpeg_quality  # 提高JPEG质量
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
        """优化后的图片处理（2x2布局）"""
        images = sorted(
            [f for f in os.listdir(image_folder) if f.lower().endswith(SUPPORTED_IMAGE_EXT)],
            key=lambda x: os.path.splitext(x)[0]
        )

        if not images:
            return

        # 新版布局参数
        IMAGES_PER_PAGE = 4  # 改为4张/页
        COLS = 2  # 2列布局
        ROWS = 2  # 2行布局
        MARGIN_X = 10
        MARGIN_Y = 15
        SPACING = 5

        # 计算单元格尺寸（增大显示区域）
        page_width_avail = MAX_PAGE_WIDTH - 2 * MARGIN_X
        cell_width = (page_width_avail - (COLS - 1) * SPACING) / COLS
        page_height_avail = MAX_PAGE_HEIGHT - MARGIN_Y - 15
        cell_height = (page_height_avail - (ROWS - 1) * SPACING) / ROWS

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                for i, img_file in enumerate(images):
                    # 分页控制
                    if i % IMAGES_PER_PAGE == 0:
                        self.pdf.add_page()

                    # 计算位置（新版布局计算）
                    position = i % IMAGES_PER_PAGE
                    row = position // COLS
                    col = position % COLS
                    x = MARGIN_X + col * (cell_width + SPACING)
                    y = MARGIN_Y + row * (cell_height + SPACING)

                    # 图片处理流程
                    img_path = os.path.join(image_folder, img_file)
                    temp_path = os.path.join(temp_dir, f"compressed_{i}.jpg")

                    with Image.open(img_path) as img:
                        # 保留透明度通道
                        if img.mode == 'RGBA':
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[3])
                            img = background

                        # 优化压缩逻辑
                        if self.compress_ratio < 1:
                            new_size = (
                                int(img.width * self.compress_ratio),
                                int(img.height * self.compress_ratio)
                            )
                            img = img.resize(new_size, Image.Resampling.LANCZOS)

                        # 高质量保存
                        img.save(
                            temp_path,
                            quality=self.jpeg_quality,
                            optimize=True,
                            subsampling=0  # 关闭色度抽样
                        )

                    # 精确计算显示尺寸
                    with Image.open(temp_path) as compressed_img:
                        # 转换为毫米单位
                        mm_width = compressed_img.width * 0.264583
                        mm_height = compressed_img.height * 0.264583

                        # 自适应缩放（使用全部空间）
                        width_ratio = cell_width / mm_width
                        height_ratio = cell_height / mm_height
                        scale_ratio = min(width_ratio, height_ratio)

                        # 应用最佳缩放
                        scaled_width = mm_width * scale_ratio
                        scaled_height = mm_height * scale_ratio
                        x_offset = (cell_width - scaled_width) / 2
                        y_offset = (cell_height - scaled_height) / 2

                        # 添加高精度图片
                        self.pdf.image(
                            temp_path,
                            x=x + x_offset,
                            y=y + y_offset,
                            w=scaled_width,
                            h=scaled_height,
                            keep_aspect_ratio=True
                        )

            except Exception as e:
                logging.error(f"图片处理异常: {str(e)}")

    def save(self, output_path):
        self.pdf.output(output_path)


def convert_file(txt_path, output_dir, root_folder):
    """文件转换流程"""
    try:
        # 视频文件检测
        txt_dir = os.path.dirname(txt_path)
        if any(f.lower().endswith(VIDEO_EXT) for f in os.listdir(txt_dir)):
            logging.info(f"发现视频文件，跳过目录：{os.path.basename(txt_dir)}")
            return False

        # 生成路径标识
        relative_path = os.path.relpath(txt_dir, root_folder)
        path_parts = [sanitize_filename(p) for p in relative_path.split(os.sep) if p]

        # 文件名生成规则
        base_name = sanitize_filename(os.path.splitext(os.path.basename(txt_path))[0])
        folder_name = "_".join(path_parts[-3:]) if len(path_parts) >= 3 else "_".join(path_parts) or "root"
        user_id = path_parts[0].split('_')[1]
        output_name = f"xhs_图文_{folder_name}_{base_name}.pdf"

        # 这里加一个 if，如果这个 dict 有这个 uid
        sector = user_id_dict.get(user_id)
        if sector:
            print('有赛道：' + sector)
            output_dir_with_folder = output_dir + '/' + sector + '/' + relative_path.split('/')[1]
            os.makedirs(output_dir_with_folder, exist_ok=True)
            output_path = os.path.join(output_dir_with_folder, output_name)

        else:
            print('无赛道' )
            output_dir_with_folder = output_dir + '/' + relative_path.split('/')[1]
            os.makedirs(output_dir_with_folder, exist_ok=True)
            output_path = os.path.join(output_dir_with_folder, output_name)


        # 存在性检查
        if os.path.exists(output_path):
            logging.info(f"文件已存在，跳过转换：{output_name}")
            return False

        # 执行转换
        converter = PDFConverter(compress_ratio=0.8, jpeg_quality=95)
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
    target_folder = "/Users/penghao/GitHub/Spider_XHS/赛道汇总"
    process_folder(target_folder)
    root_folder = '/Volumes/PenghaoMac2/XHS data'

    output_dir = os.path.join(root_folder, "小红书图文PDF输出")
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
    # /Users/penghao/Documents/GitHub/Spider_XHS/datas/media_datas
    main()