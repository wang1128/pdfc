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


def process_audio(wav_path):
    """处理单个音频文件"""
    try:
        dir_path = os.path.dirname(wav_path)
        file_name = os.path.basename(wav_path)
        base_name = os.path.splitext(file_name)[0]
        txt_path = os.path.join(dir_path, f"{base_name}.txt")

        # 跳过已处理文件
        if os.path.exists(txt_path):
            return True

        model = create_model()
        result = model.generate(input=wav_path)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result[0]["text"])

        return True
    except Exception as e:
        print(f"\n处理失败: {wav_path}\n{str(e)}")
        return False


def process_folder(folder_path):
    """递归处理文件夹"""
    wav_files = []

    # 递归扫描目录
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".wav"):
                wav_files.append(os.path.join(root, file))

    if not wav_files:
        print("错误：未找到WAV文件")
        return False
    print('start')
    # 创建进度条
    with tqdm(total=len(wav_files), desc="处理进度", unit="file") as pbar:
        success_count = 0
        for wav_path in wav_files:
            if process_audio(wav_path):
                success_count += 1
            pbar.update(1)
            pbar.set_postfix({"成功率": f"{success_count / len(wav_files):.1%}"})

    print(f"\n处理完成: 成功{success_count}个, 失败{len(wav_files) - success_count}个")
    return True


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="批量音频转文本工具")
    # parser.add_argument("-i", "--input",
    #                     type=str,
    #                     required=True,
    #                     help="输入文件夹路径（支持嵌套子目录）")
    # args = parser.parse_args()

    # root_folder = '/Users/penghao/Documents/GitHub/Spider_XHS/datas'
    root_folder = '/Users/penghao/Documents/GitHub/pdfc'

    if not os.path.isdir(root_folder):
        print(f"错误：路径不存在或不是文件夹 - {root_folder}")
        exit(1)
    print("start")
    process_folder(root_folder)