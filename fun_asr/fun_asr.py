# -*- coding: utf-8 -*-

import os
import sys
import traceback
import torch
from funasr import AutoModel

# 固定参数配置
INPUT_FOLDER = "/Users/penghao/Documents/GitHub/pdfc/fun_asr"  # 写死的输入文件夹路径（相对当前脚本所在目录）
DEFAULT_OUTPUT_FOLDER = "./conversion_output"  # 默认输出到当前目录下的文件夹

# 全局模型缓存
funasr_models = {}


def create_model():
    """创建中文语音识别模型（固定配置）"""
    # 模型路径配置（优先本地路径）
    model_paths = {
        "asr": 'tools/asr/models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch',
        "vad": 'tools/asr/models/speech_fsmn_vad_zh-cn-16k-common-pytorch',
        "punc": 'tools/asr/models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch'
    }

    # 检查本地模型路径
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
        print(f"\n模型加载完成（运行设备：{device.upper()}）")
        funasr_models["zh"] = model
    return funasr_models["zh"]


def process_folder(input_folder, output_folder):
    """处理整个输入文件夹"""
    # 创建输出目录
    os.makedirs(output_folder, exist_ok=True)

    # 获取输入目录下的所有WAV文件
    wav_files = [
        f for f in os.listdir(input_folder)
        if f.lower().endswith(".wav")
    ]

    if not wav_files:
        print(f"错误：输入目录中没有WAV文件 - {os.path.abspath(input_folder)}")
        return False

    model = create_model()

    print(f"\n开始处理音频文件（共{len(wav_files)}个）:")
    for filename in wav_files:
        try:
            file_path = os.path.join(input_folder, filename)
            print(f"\n正在处理：{filename}")

            # 执行语音识别
            result = model.generate(input=file_path)
            text = result[0]["text"]

            # 生成输出文件路径
            output_filename = f"{os.path.splitext(filename)[0]}_conversion.txt"
            output_path = os.path.join(output_folder, output_filename)

            # 写入结果
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"{file_path}|{filename}|ZH|{text}")

            print(f"  结果已保存至：{output_path}")

        except Exception as e:
            print(f"  处理失败：{str(e)}")
            print(traceback.format_exc())

    return True


if __name__ == "__main__":
    # 获取脚本所在目录的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 构建完整输入路径
    input_folder = os.path.join(script_dir, INPUT_FOLDER)

    # 验证输入路径是否存在
    if not os.path.exists(input_folder):
        print(f"错误：输入目录不存在 - {os.path.abspath(input_folder)}")
        print("请创建 'input_wavs' 文件夹并放入WAV文件")
        sys.exit(1)

    # 设置输出路径
    output_folder = os.path.join(script_dir, DEFAULT_OUTPUT_FOLDER.lstrip("./"))

    # 执行处理
    success = process_folder(input_folder, output_folder)

    if success:
        print(f"\n处理完成！所有结果文件保存在：{os.path.abspath(output_folder)}")
    else:
        print("\n处理过程中发生错误，请检查输入文件格式")