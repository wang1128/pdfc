"""
txt2pdf_converter.py 最终优化版
修复字体设置问题，增强稳定性
"""
import logging
import os
import random
import re
import sys
import tempfile
import glob
from fpdf import FPDF
from fontTools.ttLib import TTFont
from PIL import Image

# 配置参数
DEFAULT_FONT_SIZE = 12
CONTENT_FONT_SIZE = 14
MAX_PAGE_WIDTH = 190
MAX_PAGE_HEIGHT = 270
SUPPORTED_IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
VIDEO_EXT = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')
LOG_FILE = "conversion.log"

import json
import os
import logging
from datetime import datetime


def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('conversion.log'),
            logging.StreamHandler()
        ]
    )


def parse_hybrid_time(time_str):
    """解析混合格式时间（支持时间戳和特殊格式字符串）"""
    try:
        # 尝试解析为时间戳（字符串或数字格式）
        timestamp = int(time_str)
        return datetime.fromtimestamp(timestamp)
    except (ValueError, TypeError):
        try:
            # 尝试解析为特殊格式字符串
            return datetime.strptime(time_str, "%Y-%m-%d %H.%M.%S")
        except (ValueError, TypeError):
            logging.warning(f"无法识别的时间格式: {time_str}")
            return None


def convert_video_data(data):
    """处理单个视频数据"""
    # 提取统计数据（带多层保护）
    stats = data.get('statistics', {})
    author = data.get('author')
    if not author:
        logging.warning(f"no author: {author}")


    # 处理视频信息
    video_info = {
        'create_time': parse_hybrid_time(data.get('create_time')),
        'desc': data.get('desc', '暂无描述').split('，版本过低')[0],  # 清理描述文本
        'aweme_id': data.get('aweme_id', '未知ID'),
        'digg_count': stats.get('digg_count', 0),
        'comment_count': stats.get('comment_count', 0),
        'collect_count': stats.get('collect_count', 0),
        'share_count': stats.get('share_count', 0)
        ,'nickname':author.get('nickname','未知ID')
        , 'follower_count': author.get('follower_count', 0)
    }

    # 处理视频播放地址
    if video := data.get('video'):
        if play_addr := video.get('play_addr'):
            video_info['url_list'] = play_addr.get('url_list', [])
    video_info.setdefault('url_list', [])

    return video_info


def generate_content(video_info):
    """生成详情文本内容"""
    # 格式化时间信息
    time_str = video_info['create_time'].strftime('%Y-%m-%d %H:%M:%S') \
        if video_info['create_time'] else "未知时间"

    # 格式化统计数字
    def format_num(num):
        return f"{int(num):,}" if isinstance(num, (int, float)) else str(num)

    # 构建内容模板
    return f"""【视频详情】
发布时间：{time_str}
视频ID：{video_info['aweme_id']}
作者：{video_info['nickname']}
关注人数：{video_info['follower_count']}
──────────────
点赞：{format_num(video_info['digg_count'])}
评论：{format_num(video_info['comment_count'])}
收藏：{format_num(video_info['collect_count'])}
分享：{format_num(video_info['share_count'])}
──────────────
视频描述：
{video_info['desc']}

原始视频链接：
{next(iter(video_info['url_list']), '链接获取失败')}
"""


def json_to_detail(json_path):
    """处理新版JSON文件转换"""
    try:
        # 路径验证
        if not os.path.isfile(json_path):
            logging.error(f"文件不存在: {json_path}")
            return False

        output_path = os.path.join(os.path.dirname(json_path), "detail.txt")
        if os.path.exists(output_path):
            logging.info(f"已存在转换结果: {output_path}")
            return True

        # 读取并解析JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # 处理数组格式数据
        if isinstance(raw_data, list):
            if not raw_data:
                logging.warning("空JSON数组")
                return False
            video_data = convert_video_data(raw_data[0])
        else:
            video_data = convert_video_data(raw_data)

        # 生成并写入文件
        content = generate_content(video_data)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logging.info(f"成功生成: {output_path}")
        return True

    except json.JSONDecodeError as e:
        logging.error(f"JSON解析失败: {e}")
    except Exception as e:
        logging.error(f"处理异常: {e}")

    return False


def process_directory_json(root_dir):
    """遍历目录处理所有JSON文件"""
    if not os.path.isdir(root_dir):
        logging.error(f"无效目录: {root_dir}")
        return

    logging.info(f"开始处理目录: {root_dir}")
    # 遍历根目录及其所有子目录
    for root, _, files in os.walk(root_dir):
        # 遍历当前目录下的所有文件
        for file in files:
            # 检查是否为JSON文件（不限定文件名）
            if file.endswith('.json'):
                json_path = os.path.join(root, file)
                logging.info(f"正在处理: {json_path}")
                # 调用处理函数并记录结果
                try:
                    if json_to_detail(json_path):
                        logging.info(f"处理成功: {json_path}")
                    else:
                        logging.warning(f"处理失败: {json_path}")
                except Exception as e:
                    logging.error(f"处理异常（{e}）: {json_path}")






def get_unique_filepath(filepath):
    """
    生成一个不重复的文件路径，如果原路径存在，则添加后缀数字。
    """
    base, ext = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(filepath):
        filepath = f"{base}_{counter}{ext}"
        counter += 1
    return filepath


def rename_txt_files_to_audio_prefix(root_path):
    """
    遍历所有文件夹，将txt文件重命名为audio_前缀格式。
    """
    for foldername, subfolders, filenames in os.walk(root_path):
        for filename in filenames:
            if filename.endswith('.txt') and not filename.startswith('audio_') and not filename.startswith('detail'):
                old_path = os.path.join(foldername, filename)
                new_name = f"audio.txt"
                new_path = os.path.join(foldername, new_name)

                # 处理可能的重名情况
                new_path = get_unique_filepath(new_path)

                os.rename(old_path, new_path)
                print(f"重命名成功: {old_path} -> {new_path}")

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
    logging.getLogger('fontTools').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('fpdf').setLevel(logging.WARNING)


def sanitize_filename(name):
    """生成安全文件名（保留中日文字符）"""
    clean_name = re.sub(r'[\\/*?:"<>|]', "-", name)
    clean_name = re.sub(r'[\t\n\r\f\v]+', '_', clean_name)
    return clean_name[:120]


class FileOutput:
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
            ("MicrosoftYaHei", "C:/Windows/Fonts/msyh.ttc"),  # 微软雅黑（常规）
            ("SimSun", "C:/Windows/Fonts/simsun.ttc"),  # 宋体
            ("SegoeUIEmoji", "C:/Windows/Fonts/seguiemj.ttf")  # Segoe UI Emoji
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
                text=para,
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
        """增强封面处理功能"""
        logging.info(f"开始处理封面图片：{image_path}")
        try:
            with Image.open(image_path) as img:
                # 转换颜色模式并计算尺寸
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background

                width_mm = img.width * 0.0846  # 像素转毫米（300dpi）
                height_mm = img.height * 0.0846

                # 创建临时PDF页面
                self.pdf.add_page(format=(width_mm + 20, height_mm + 20))
                x = (self.pdf.w - width_mm) / 2
                y = (self.pdf.h - height_mm) / 2

                # 使用原始尺寸保存临时文件

                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    img.save(tmp.name,
                             format='JPEG',
                             quality=50,  # 质量参数（网页2、4、6）
                             optimize=True,  # 哈夫曼优化（网页4、6）
                             progressive=True)  # 渐进式加载（网页4、6）

                    # PDF插入（保持原逻辑）
                    self.pdf.image(tmp.name, x=x, y=y, w=width_mm)

                logging.info(f"封面图片压缩成功：{image_path}")
                return True

        except Exception as e:
            logging.error(f"封面处理失败: {str(e)}", exc_info=True)
            return False

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


def extract_number(filename):
    """通用数字提取函数"""
    basename = os.path.basename(filename)
    match = re.search(r'(\d+)', basename)
    return int(match.group(1)) if match else 0


def convert_video_folder(folder_path, output_dir, root_folder):
    """
    处理视频文件夹转换的完整函数
    生成路径示例：
    输入：/test/老于/2024-05-21 18.53.55_标题
    输出：视频PDF输出/老于/douyin_视频_老于_2024-05-21-18-53-55_标题.pdf
    """
    # ===================== 4. 智能路径生成 =====================
    # 4.1 提取路径要素
    relative_path = os.path.relpath(folder_path, root_folder)
    path_parts = [p for p in relative_path.split(os.sep) if p]

    # 4.2 确定父文件夹（test的下一层）
    parent_folder = "未分类"
    if len(path_parts) > 0:
        parent_folder = sanitize_filename(path_parts[0])

    # 4.3 处理当前文件夹名称
    current_folder = os.path.basename(folder_path)
    name_parts = current_folder.split('_', 1)  # 分割日期和标题

    # 日期标准化处理（处理 2024-05-21 18.53.55 格式）
    date_part = re.sub(r'[ :.]+', '-', name_parts[0]) if len(name_parts) > 0 else "无日期"

    # 标题处理（截断至60字符）
    title_part = name_parts[1] if len(name_parts) > 1 else "无标题"
    title_part = sanitize_filename(title_part)[:60].rstrip('_')

    # 4.4 构建最终路径
    output_subdir = os.path.join(output_dir, parent_folder)
    output_subdir = output_dir
    os.makedirs(output_subdir, exist_ok=True)

    output_name = f"douyin_视频_{parent_folder}_{date_part}_{title_part}.pdf"
    output_path = os.path.join(output_subdir, output_name)

    if os.path.exists(output_path):
        print('已有文件：' + output_path)
        return True


    try:
        # ===================== 1. 必要文件验证 =====================
        detail_path = os.path.join(folder_path, 'detail.txt')
        if not os.path.exists(detail_path):
            raise FileNotFoundError("缺失detail.txt")

        # 获取排序后的文件列表
        audio_files = sorted(
            glob.glob(os.path.join(folder_path, 'audio*.txt')),
            key=extract_number
        )
        cover_files = sorted(
            [f for ext in SUPPORTED_IMAGE_EXT
             for f in glob.glob(os.path.join(folder_path, f'*cover*{ext}'))],
            key=extract_number
        )

        if not audio_files:
            raise FileNotFoundError("未找到audio*.txt文件")
        # if not cover_files:
        #     raise FileNotFoundError("未找到cover图片文件")

        # ===================== 2. 内容读取处理 =====================
        # 读取detail.txt内容（带异常字符处理）
        with open(detail_path, 'rb') as f:
            detail_text = f.read().decode('utf-8', errors='replace')

        # 合并音频文稿内容
        audio_text = []
        for af in audio_files:
            try:
                with open(af, 'rb') as f:
                    audio_text.append(f.read().decode('utf-8', errors='replace'))
            except Exception as e:
                logging.warning(f"音频文件读取失败：{af} - {str(e)}")
                audio_text.append("[损坏内容]")

        # ===================== 3. PDF生成核心 =====================
        converter = PDFConverter()

        # 3.1 添加封面图片（多封面支持）
        for cover in cover_files:
            if not converter.add_cover_image(cover):
                logging.warning(f"封面添加失败：{cover}")

        # 3.2 添加详情内容
        converter.pdf.add_page()
        converter.add_text(detail_text.strip())

        # 3.3 添加音频文稿
        converter.pdf.add_page()
        converter.add_section_title("视频稿（口播搞）")
        converter.add_text('\n'.join(audio_text).strip())



        # ===================== 5. 冲突处理机制 =====================
        # 处理文件重名（自动添加序号）
        # counter = 1
        # original_output = output_path
        # while os.path.exists(output_path):
        #     new_name = f"{os.path.splitext(output_name)[0]}_{counter}.pdf"
        #     output_path = os.path.join(output_subdir, new_name)
        #     counter += 1
        #     if counter > 99:  # 防止无限循环
        #         raise Exception("文件重名超过最大限制")

        # ===================== 6. 最终保存操作 =====================
        converter.save(output_path)
        logging.info(f"转换成功：{os.path.relpath(output_path, output_dir)}")
        return True

    except Exception as e:
        logging.error(f"转换失败：{folder_path}\n错误详情：{str(e)}", exc_info=True)
        return False


def convert_normal_txt(txt_path, output_dir, root_folder):
    try:
        with open(txt_path, "rb") as f:
            text = f.read().decode('utf-8', errors='replace')

        converter = PDFConverter()
        converter.pdf.add_page()
        converter.add_text(text)

        txt_dir = os.path.dirname(txt_path)
        relative_path = os.path.relpath(txt_dir, root_folder)
        path_parts = [sanitize_filename(p) for p in relative_path.split(os.sep) if p]
        base_name = sanitize_filename(os.path.splitext(os.path.basename(txt_path))[0])
        folder_name = "_".join(path_parts[-3:]) or "root"
        output_name = f"douyin_{folder_name}_{base_name}.pdf"
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

    print('开始转成audio.txt')
    rename_txt_files_to_audio_prefix(root_folder)
    print('开始转info.json')
    process_directory_json(root_folder)

    output_dir_normal = os.path.join(root_folder, "普通PDF输出")
    output_dir_video = os.path.join(root_folder, "抖音PDF输出0507")
    os.makedirs(output_dir_normal, exist_ok=True)
    os.makedirs(output_dir_video, exist_ok=True)

    processed_normal = 0
    processed_video = 0

    for root, dirs, files in os.walk(root_folder):
        # 随机化子目录和文件的遍历顺序
        random.shuffle(dirs)  # 打乱子目录访问顺序
        random.shuffle(files)  # 打乱文件处理顺序

        # 跳过输出目录（逻辑不变）
        if any(os.path.abspath(root).startswith(os.path.abspath(d))
               for d in [output_dir_normal, output_dir_video]):
            continue

        # 处理视频文件夹（文件顺序已随机）
        if any(f.lower().endswith(VIDEO_EXT) for f in files):
            if convert_video_folder(root, output_dir_video, root_folder):
                processed_video += 1

        # 处理普通文本文件
        # for file in files:
        #     if file.lower().endswith('.txt') and not file.lower().startswith('audio_'):
        #         if convert_normal_txt(os.path.join(root, file), output_dir_normal, root_folder):
        #             processed_normal += 1

    logging.info(f"\n转换完成：普通文件 {processed_normal} 个，视频文件夹 {processed_video} 个")


if __name__ == "__main__":
    # /Volumes/192.168.31.67/Douyin_Downloaded
    main()