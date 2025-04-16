"""
video_to_audio_converter_v2.py
修复verbose参数错误并增强兼容性的视频转音频脚本
"""
import logging
import os
import re
from moviepy import VideoFileClip, config
import subprocess

# 配置参数
VIDEO_NAME = "video.mp4"  # 主视频文件名（支持其他扩展名）
AUDIO_NAME = "audio.wav"  # 输出音频文件名
LOG_FILE = "audio_conversion_v2.log"
VIDEO_EXTS = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')


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


def sanitize_filename(name):
    """生成安全文件名（保留中日文字符）"""
    clean_name = re.sub(r'[\\/*?:"<>|]', "-", name)
    return clean_name[:120]


def check_ffmpeg():
    """验证FFmpeg安装"""
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        if 'ffmpeg version' in result.stderr:
            return True
        # MacOS特殊路径处理
        config.FFMPEG_BINARY = "/opt/homebrew/bin/ffmpeg"
        return os.path.exists(config.FFMPEG_BINARY)
    except Exception as e:
        logging.error(f"FFmpeg检查失败: {str(e)}")
        return False


def convert_video_to_audio(video_path, audio_path):
    """视频转音频核心逻辑"""
    try:
        # 使用with语句确保资源释放
        with VideoFileClip(video_path) as video:
            audio = video.audio
            audio.write_audiofile(
                audio_path,
                codec='pcm_s16le',  # WAV格式
                fps=44100,  # CD音质
                logger=None  # 禁用详细日志[4](@ref)
            )
            audio.close()
        return True
    except Exception as e:
        logging.error(f"转换失败：{video_path} - {str(e)}")
        # 尝试修复损坏的视频头
        if "failed to read the first frame" in str(e):
            return repair_video(video_path, audio_path)
        return False


def repair_video(input_path, output_path):
    """视频修复预处理"""
    try:
        temp_path = os.path.join(os.path.dirname(input_path), "temp_repaired.mp4")
        cmd = [
            config.FFMPEG_BINARY,
            '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-movflags', '+faststart',
            temp_path
        ]
        subprocess.run(cmd, check=True)

        with VideoFileClip(temp_path) as video:
            audio = video.audio
            audio.write_audiofile(output_path,
                                  codec='pcm_s16le',
                                  fps=44100)
        os.remove(temp_path)
        return True
    except Exception as e:
        logging.error(f"视频修复失败: {str(e)}")
        return False


def process_directory(folder_path):
    """处理单个目录"""
    video_files = [
        f for f in os.listdir(folder_path)
        if os.path.splitext(f)[0].lower() == 'video'
           and f.lower().endswith(VIDEO_EXTS)
    ]

    if not video_files:
        return False

    target_audio = os.path.join(folder_path, AUDIO_NAME)
    if os.path.exists(target_audio):
        return False

    # 处理第一个符合条件的视频文件
    source_video = os.path.join(folder_path, video_files[0])

    logging.info(f"开始转换：{source_video}")
    return convert_video_to_audio(source_video, target_audio)


def main():
    setup_logging()

    if not check_ffmpeg():
        logging.error("FFmpeg未正确安装，请参考：https://ffmpeg.org/download.html")
        return

    root_folder = input("请输入根文件夹路径：").strip()
    if not os.path.isdir(root_folder):
        logging.error("错误：路径不存在或不是文件夹")
        return

    processed = 0
    for root, dirs, files in os.walk(root_folder):
        # 跳过已存在音频文件的目录
        if any(f.lower() == AUDIO_NAME.lower() for f in files):
            continue

        # 处理包含视频文件的目录
        video_files = [f for f in files if f.lower().startswith('video.')]
        if video_files:
            if process_directory(root):
                processed += 1

    logging.info(f"处理完成！共转换 {processed} 个音频文件")


if __name__ == "__main__":
    # /Users/penghao/Documents/GitHub/Spider_XHS/datas
    main()