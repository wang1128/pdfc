import os, sys
import pytesseract
from PIL import Image
import pytesseract

import os
import pytesseract

# 强制指定路径配置
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
os.environ['TESSDATA_PREFIX'] = '/opt/homebrew/share/tessdata/'  # 精确到tessdata目录

def ocr_image(image_path):
    try:
        img = Image.open(image_path)
        # 使用如下任一配置方式
        # text = pytesseract.image_to_string(img, lang='chi_sim')  # 方式一：依赖环境变量
        # 或
        text = pytesseract.image_to_string(img, lang='chi_sim',
              config='--tessdata-dir /opt/homebrew/share/tessdata/')  # 方式二：直接指定目录
        return text.strip()
    except Exception as e:
        print(f"识别失败：{str(e)}")
        return None

def get_image_files(folder_path):
    """获取文件夹及其子文件夹中的所有图片文件"""
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']
    for root, _, files in os.walk(folder_path):
        for file in files:
            if os.path.splitext(file)[1].lower() in image_extensions:
                yield os.path.join(root, file)


def process_folder(folder_path):
    """处理单个文件夹"""
    txt_path = os.path.join(folder_path, "pic_content.txt")
    content = []

    for img_path in get_image_files(folder_path):
        print(f"正在识别：{img_path}")
        text = ocr_image(img_path)
        if text:
            content.append(f"文件：{os.path.basename(img_path)}")
            content.append(text)
            content.append("\n" + "-" * 50 + "\n")

    if content:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
        print(f"识别结果已保存至：{txt_path}")


def get_valid_path():
    """获取有效的路径输入"""
    while True:
        path = input("请输入文件夹路径：").strip()
        path = path.strip('"').strip("'")  # 去除拖拽产生的引号
        if os.path.isdir(path):
            return path
        print(f"路径无效：{path}")


if __name__ == "__main__":
    # 支持命令行参数和交互式输入
    if len(sys.argv) > 1:
        folder_path = sys.argv[1].strip('"').strip("'")
    else:
        folder_path = get_valid_path()

    # 遍历处理所有子文件夹
    for root, dirs, _ in os.walk(folder_path):
        print(f"\n正在处理文件夹：{root}")
        process_folder(root)
    print("\n中文识别已完成！")