"""
video_to_audio_converter_v3.py
增强版视频转音频脚本
功能：
- 检查audio.wav存在性并跳过处理
- 自动修复损坏视频文件
- 中文字符路径兼容
- 详细日志记录
"""
import logging
import os
import re
import subprocess
from datetime import datetime
from moviepy import VideoFileClip, config

# 配置参数
VIDEO_NAME = "video"  # 主视频文件名（不含扩展）
AUDIO_NAME = "audio.wav"
LOG_FILE = "conversion.log"
VIDEO_EXTS = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')


def setup_logging():
    """初始化日志系统"""
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)


def check_ffmpeg():
    """验证FFmpeg环境"""
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
    """核心转换逻辑"""
    try:
        with VideoFileClip(video_path) as video:
            audio = video.audio
            audio.write_audiofile(
                audio_path,
                codec='pcm_s16le',
                fps=44100,
                logger=None  # 禁用详细日志
            )
            return True
    except Exception as e:
        logging.error(f"转换失败：{video_path} - {str(e)}")
        # os.remove(video_path)
        # print(f"已删除： {video_path}")
        ## 不修了，直接删
        # if "failed to read the first frame" in str(e):
        #     ####
        #     return repair_video(video_path, audio_path)
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
    # 检查目标音频文件存在性
    target_audio = os.path.join(folder_path, AUDIO_NAME)
    if os.path.isfile(target_audio):  # 精确判断文件存在性[2,6](@ref)
        logging.info(f"跳过目录：{folder_path}（{AUDIO_NAME}已存在）")
        print(f"[跳过] {folder_path} 已存在音频文件")
        return False

    # 查找视频文件
    video_files = [
        f for f in os.listdir(folder_path)
        if f.lower().startswith(VIDEO_NAME.lower())
           and f.lower().endswith(VIDEO_EXTS)
    ]

    if not video_files:
        return False

    # 处理第一个符合条件的视频文件
    source_video = os.path.join(folder_path, video_files[0])

    logging.info(f"开始转换：{source_video}")
    return convert_video_to_audio(source_video, target_audio)


def main():
    setup_logging()

    # if not check_ffmpeg():
    #     logging.error("FFmpeg未正确安装，请参考：https://ffmpeg.org/download.html")
    #     return

    # root_folder = input("请输入根文件夹路径：").strip()
    # if not os.path.isdir(root_folder):
    #     logging.error("错误：路径不存在或不是文件夹")
    #     return
    # root_folder = '/Users/penghao/Documents/GitHub/Spider_XHS/datas'
    # /Volumes/Penghao/xhs_2025/media_datas
    # /Users/penghao/GitHub/Spider_XHS/datas/media_datas/挣钱/彦页同学_6754536a000000001d02c042/15高中生赚10000块！（大胆尝试！）_67e5630c00000000090152ac
    # root_folder = '/Volumes/PenghaoMac2/XHS data'
    root_folder = 'G:\\XHS data'
    root_folder = 'D:\\Users\\penghao\\Downloads'
    processed = 0
    for root, dirs, files in os.walk(root_folder):
        if process_directory(root):
            processed += 1

    logging.info(f"处理完成！共转换 {processed} 个音频文件")
    print(f"\n{'-' * 40}")
    print(f"转换报告：\n- 成功转换：{processed}\n- 日志文件：{os.path.abspath(LOG_FILE)}")


if __name__ == "__main__":
    main()