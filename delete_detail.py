import os
import shutil,sys

def delete_detail_files(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file == "detail.txt":
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"已删除: {file_path}")
                except Exception as e:
                    print(f"删除失败 {file_path}: {e}")

# 使用方法
if len(sys.argv) < 2:
    root_folder = input("请输入根文件夹路径：").strip()
else:
    root_folder = sys.argv[1]
root_folder = "/path/to/your/folder"  # 替换为你的文件夹路径
delete_detail_files(root_folder)
print("操作完成")