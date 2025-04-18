import os
import sys


def delete_video_files(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        video_path = os.path.join(dirpath, 'video.mp4')
        audio_path = os.path.join(dirpath, 'audio.wav')

        # 检查两个文件是否同时存在
        if os.path.isfile(video_path) and os.path.isfile(audio_path):
            try:
                os.remove(video_path)
                print(f"已删除： {video_path}")
            except Exception as e:
                print(f"删除失败 ({video_path}): {str(e)}")


def main():
    # if len(sys.argv) == 2:
    #     target_dir = sys.argv[1]
    # else:
    #     target_dir = input("请输入要扫描的文件夹路径： ").strip()

    target_dir = '/Users/penghao/Documents/GitHub/Spider_XHS/datas'

    if not os.path.isdir(target_dir):
        print("错误：路径无效或不是文件夹")
        return

    print("开始扫描...")
    delete_video_files(target_dir)
    print("操作完成")


if __name__ == "__main__":
    main()