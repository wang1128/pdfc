import requests
import json


def test_conversion_service():
    # 服务端配置
    server_url = "http://localhost:8081/convert"

    # 替换为实际要测试的视频目录路径（确保服务端有访问权限）
    test_path = "/path/to/your/video/folder"  # 示例路径："/data/media/videos"

    # 构造请求数据
    payload = {
        "path": test_path
    }

    print("视频转音频服务测试客户端")
    print("=" * 40)
    print(f"目标路径: {test_path}")
    print(f"服务端点: {server_url}")

    try:
        # 发送POST请求
        response = requests.post(server_url, json=payload)

        # 解析响应
        status_code = response.status_code
        response_data = response.json()

        print("\n响应状态码:", status_code)
        print("响应内容:")
        print(json.dumps(response_data, indent=2))

        # 处理不同状态码
        if status_code == 202:
            print("\n✅ 转换任务已成功提交")
            print("提示：转换是异步进行的，请查看服务端日志了解进度")
        elif status_code == 400:
            print("\n❌ 请求验证失败：")
            if "error" in response_data:
                print("问题描述:", response_data["error"])
            print("请检查：")
            print("- 路径是否存在")
            print("- 路径格式是否正确（应使用绝对路径）")
            print("- 路径是否包含中文字符等特殊字符")
        elif status_code == 500:
            print("\n❌ 服务端处理异常：")
            print("错误信息:", response_data.get("error", "未知错误"))
            print("建议检查服务端日志获取详细信息")

    except requests.exceptions.ConnectionError:
        print("\n❌ 连接服务端失败，请检查：")
        print("- 服务是否正在运行（检查端口8081）")
        print("- 防火墙设置是否允许访问")
        print("- 服务地址是否正确")
    except Exception as e:
        print("\n❌ 发生未预期错误:", str(e))


if __name__ == "__main__":
    test_conversion_service()