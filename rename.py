import os

folder = r'G:\\Douyin_Downloaded\\user_金枪大叔_MS4wLjABAAAAT4iFvoTOtlJCDuUMyovtft5NLQOnQZ-HECl7EGe-rT0\\抖音PDF输出'

for filename in os.listdir(folder):
    if filename.startswith('douyin_视频_') and filename.endswith('.pdf'):
        new_name = f'金枪大叔{filename}'
        os.rename(
            os.path.join(folder, filename),
            os.path.join(folder, new_name)
        )
        print(f'已重命名: {filename} -> {new_name}')