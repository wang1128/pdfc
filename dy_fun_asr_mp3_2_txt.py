# -*- coding: utf-8 -*-
import os
import argparse
import traceback
import torch
from tqdm import tqdm
from funasr import AutoModel

# 全局模型缓存
funasr_models = {}


def create_model():
    """创建中文语音识别模型（固定配置）"""
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
        # if torch.cuda.is_available() else "cpu"
        print(device)
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


def process_audio(mp3_path):
    """处理单个音频文件"""
    try:
        dir_path = os.path.dirname(mp3_path)
        file_name = os.path.basename(mp3_path)
        base_name = os.path.splitext(file_name)[0]
        txt_path = os.path.join(dir_path, f"{base_name}.txt")

        # 新增：检查目录下是否存在以 "audio_" 开头的文件
        skip_processing = False
        for filename in os.listdir(dir_path):
            if filename.startswith('audio') :
                print(f"发现以 audio_ 开头的文件: {filename}，跳过处理")
                skip_processing = True
                break  # 发现一个即终止循环



        # 任一文件存在则跳过
        if os.path.exists(txt_path) or skip_processing:
            print(dir_path)
            print("已处理, 有文件" + dir_path + filename)
            return True

        model = create_model()
        result = model.generate(input=mp3_path)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result[0]["text"])

        return True
    except Exception as e:
        print(f"\n处理失败: {mp3_path}\n{str(e)}")
        return False


def process_folder(folder_path):
    """递归处理文件夹"""
    mp3_files = []

    # 递归扫描目录
    for root, _, files in os.walk(folder_path):
        # 先检查当前目录是否存在 audio.txt
        if os.path.exists(os.path.join(root, "audio.txt")):
            print(root + 'find audio.txt')
            continue  # 跳过包含 audio.txt 的整个目录

        for file in files:
            if file.lower().endswith(".mp3"):
                mp3_files.append(os.path.join(root, file))

    if not mp3_files:
        print("错误：未找到mp3文件")
        return False
    print('start')
    # 创建进度条
    with tqdm(total=len(mp3_files), desc="处理进度", unit="file") as pbar:
        success_count = 0
        for mp3_path in mp3_files:
            if process_audio(mp3_path):
                success_count += 1
            pbar.update(1)
            pbar.set_postfix({"成功率": f"{success_count / len(mp3_files):.1%}"})

    print(f"\n处理完成: 成功{success_count}个, 失败{len(mp3_files) - success_count}个")
    return True


if __name__ == "__main__":
    print("start fun asr")
    root_folder = input("请输入根文件夹路径：").strip()

    # root_folder = '/Users/penghao/Documents/GitHub/Spider_XHS/datas/media_datas'
    # root_folder = '/Users/penghao/Downloads/pdfc/fun_asr'
    # root_folder = '/Volumes/PenghaoMac2/XHS data'
    # root_folder = 'D:\\Users\\penghao\\Downloads'

    if not os.path.isdir(root_folder):
        print(f"错误：路径不存在或不是文件夹 - {root_folder}")
        exit(1)
    create_model()  # 预加载模型
    print("create_model")
    process_folder(root_folder)