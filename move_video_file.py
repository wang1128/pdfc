import os
import shutil
import sys


def move_video_files(source_dir, target_base_dir):
    for dirpath, _, filenames in os.walk(source_dir):
        video_path = os.path.join(dirpath, 'video.mp4')
        audio_path = os.path.join(dirpath, 'audio.wav')

        # 检查两个文件是否同时存在
        if os.path.isfile(video_path) and os.path.isfile(audio_path):
            # 计算相对路径
            relative_path = os.path.relpath(dirpath, source_dir)
            # 构建目标目录路径
            target_dir = os.path.join(target_base_dir, relative_path)

            # 创建目标目录（若不存在）
            os.makedirs(target_dir, exist_ok=True)

            # 构建目标文件路径
            target_video_path = os.path.join(target_dir, 'video.mp4')

            try:
                # 移动文件
                shutil.move(video_path, target_video_path)
                print(f"已移动： {video_path} -> {target_video_path}")
            except Exception as e:
                print(f"移动失败 ({video_path}): {str(e)}")


def main():
    # 解析命令行参数
    if len(sys.argv) == 3:
        source_dir = sys.argv[1]
        target_dir = sys.argv[2]
    else:
        source_dir = input("请输入源文件夹路径：").strip()
        target_dir = input("请输入目标文件夹路径（如移动硬盘路径）：").strip()

    # 校验路径有效性
    if not os.path.isdir(source_dir):
        print("错误：源路径无效或不是文件夹")
        return

    if not os.path.isdir(target_dir):
        print("错误：目标路径无效或不是文件夹")
        return

    print("开始扫描并移动视频文件...")
    move_video_files(source_dir, target_dir)
    print("操作完成")


if __name__ == "__main__":
    main()