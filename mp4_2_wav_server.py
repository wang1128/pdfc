"""
video_to_audio_service.py
视频转音频服务化版本
功能：
- 提供HTTP API接收转换任务
- 异步处理视频转音频
- 保留原有核心转换逻辑
- 跨平台路径兼容
"""

import logging
import os
import subprocess
from flask import Flask, request, jsonify
import threading
from moviepy import VideoFileClip, config

app = Flask(__name__)

# 配置参数
AUDIO_NAME = "audio.wav"
LOG_FILE = "conversion_service.log"
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
                logger=None
            )
            return True
    except Exception as e:
        logging.error(f"转换失败：{video_path} - {str(e)}")
        if os.path.exists(video_path):
            # os.remove(video_path)
            logging.info(f"已删除损坏文件：{video_path}")
        return False


def process_directory(folder_path):
    """处理单个目录"""
    target_audio = os.path.join(folder_path, AUDIO_NAME)
    if os.path.isfile(target_audio):
        logging.info(f"跳过目录：{folder_path}（{AUDIO_NAME}已存在）")
        return False

    video_files = [
        f for f in os.listdir(folder_path)
        if f.lower().startswith('video')
           and f.lower().endswith(VIDEO_EXTS)
    ]

    if not video_files:
        return False

    source_video = os.path.join(folder_path, video_files[0])
    logging.info(f"开始转换：{source_video}")
    return convert_video_to_audio(source_video, target_audio)


def process_root_folder(root_folder):
    """处理整个目录树"""
    processed = 0
    try:
        for root, dirs, files in os.walk(root_folder):
            if process_directory(root):
                processed += 1
        logging.info(f"处理完成：{root_folder} 转换 {processed} 个音频文件")
    except Exception as e:
        logging.error(f"目录处理异常：{root_folder} - {str(e)}")
    return processed


@app.route('/convert', methods=['POST'])
def handle_convert():
    """API转换接口"""
    data = request.get_json()
    if not data or 'path' not in data:
        return jsonify({"error": "Missing path parameter"}), 400

    folder_path = data['path'].strip()
    if not os.path.exists(folder_path):
        return jsonify({"error": "Path does not exist"}), 400
    if not os.path.isdir(folder_path):
        return jsonify({"error": "Path is not a directory"}), 400

    try:
        # 启动异步处理线程
        thread = threading.Thread(
            target=process_root_folder,
            args=(os.path.abspath(folder_path),)
        )
        thread.start()
        return jsonify({
            "status": "processing",
            "path": folder_path,
            "message": "Conversion started"
        }), 202
    except Exception as e:
        logging.error(f"请求处理失败：{folder_path} - {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    setup_logging()
    if not check_ffmpeg():
        logging.critical("FFmpeg环境校验失败，服务终止")
        exit(1)
    app.run(host='0.0.0.0', port=8081, threaded=True)