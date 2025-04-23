# -*- coding: utf-8 -*-
import os
import uuid
import logging
from flask import Flask, request, jsonify
from functools import lru_cache
import torch
import threading
from funasr import AutoModel

app = Flask(__name__)

# 初始化锁和标志
init_lock = threading.Lock()
initialized = False

# 服务配置
MAX_CONCURRENT_TASKS = 3
MODEL_LOCK = threading.Lock()

# 任务状态存储
tasks = {}
task_progress = {}


# 全局模型缓存
funasr_models = {}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("audio_service.log"),
        logging.StreamHandler()
    ]
)

def create_model():
    """带缓存的模型初始化"""
    try:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        logging.info(f"使用计算设备: {device}")

        model_paths = {
            "asr": 'tools/asr/models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
            "vad": 'tools/asr/models/speech_fsmn_vad_zh-cn-16k-common-pytorch',
            "punc": 'tools/asr/models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch'
        }

        path_asr = model_paths["asr"] if os.path.exists(
            model_paths["asr"]) else "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
        path_vad = model_paths["vad"] if os.path.exists(
            model_paths["vad"]) else "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
        path_punc = model_paths["punc"] if os.path.exists(
            model_paths["punc"]) else "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"

        if "zh" not in funasr_models:
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            model = AutoModel(
                model=path_asr,
                vad_model=path_vad,
                punc_model=path_punc,
                model_revision="v2.0.4",
                vad_model_revision="v2.0.4",
                punc_model_revision="v2.0.4",
                device=device,
                vad_kwargs={"max_single_segment_time": 60000}
            )
            funasr_models["zh"] = model
        return funasr_models["zh"]
    except Exception as e:
        logging.error(f"模型初始化失败: {str(e)}")
        raise RuntimeError("模型加载失败，请检查模型配置")


def initialize():
    """应用启动时初始化模型"""
    global initialized
    with init_lock:
        if not initialized:
            try:
                create_model()
                logging.info("模型预加载成功")
                initialized = True
            except Exception as e:
                logging.error(f"模型预加载失败: {str(e)}")
                raise RuntimeError("初始化失败")

initialize()




def validate_path(input_path):
    """安全路径验证"""
    if not os.path.exists(input_path):
        raise ValueError("路径不存在")
    if not os.path.isdir(input_path):
        raise ValueError("需要文件夹路径")
    if "../" in input_path:
        raise ValueError("禁止相对路径访问")


def background_task(task_id, input_path):
    """后台任务处理"""
    try:
        tasks[task_id]["status"] = "processing"

        model = create_model()
        wav_files = []
        for root, _, files in os.walk(input_path):
            wav_files.extend(
                os.path.join(root, f)
                for f in files
                if f.lower().endswith(".wav")
            )

        if not wav_files:
            tasks[task_id].update({
                "status": "failed",
                "details": {"error": "未找到WAV文件"}
            })
            return

        # 初始化进度跟踪
        total_files = len(wav_files)
        task_progress[task_id] = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "total": total_files
        }

        for idx, wav_path in enumerate(wav_files, 1):
            if tasks[task_id]["status"] == "cancelled":
                break

            txt_path = os.path.splitext(wav_path)[0] + ".txt"
            if os.path.exists(txt_path):
                task_progress[task_id]["success"] += 1
                task_progress[task_id]["processed"] = idx
                continue

            try:
                with MODEL_LOCK:
                    result = model.generate(input=wav_path)
                    text = result[0]["text"]

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
                task_progress[task_id]["success"] += 1
            except Exception as e:
                logging.error(f"处理失败: {wav_path} - {str(e)}")
                task_progress[task_id]["failed"] += 1

            task_progress[task_id]["processed"] = idx

        tasks[task_id].update({
            "status": "completed",
            "success_count": task_progress[task_id]["success"],
            "failed_count": task_progress[task_id]["failed"]
        })

    except Exception as e:
        logging.error(f"任务失败: {task_id} - {str(e)}")
        tasks[task_id].update({
            "status": "failed",
            "details": {"error": str(e)}
        })
    finally:
        task_progress.pop(task_id, None)


@app.route('/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    data = request.get_json()
    input_path = data.get('input_path')
    priority = data.get('priority', 0)

    try:
        validate_path(input_path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "input_path": os.path.abspath(input_path),
        "status": "queued",
        "priority": priority
    }

    # 启动后台线程
    threading.Thread(
        target=background_task,
        args=(task_id, input_path)
    ).start()

    return jsonify({
        "task_id": task_id,
        "status": "queued"
    })


@app.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({"error": "任务不存在"}), 404

    progress = task_progress.get(task_id, {})
    return jsonify({
        "task_id": task_id,
        "status": tasks[task_id]["status"],
        "success_count": progress.get("success", 0),
        "failed_count": progress.get("failed", 0),
        "processed": progress.get("processed", 0),
        "total": progress.get("total", 0)
    })


@app.route('/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    if task_id not in tasks:
        return jsonify({"error": "任务不存在"}), 404

    if tasks[task_id]["status"] in ("completed", "failed"):
        return jsonify({"error": "任务无法取消"}), 400

    tasks[task_id]["status"] = "cancelled"
    return jsonify({"message": "取消请求已接受"})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8082, threaded=True)