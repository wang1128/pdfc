import requests
import time

BASE_URL = "http://localhost:8082"


def test_service():
    # 创建任务
    create_response = requests.post(
        f"{BASE_URL}/tasks",
        json={
            "input_path": "/Volumes/PenghaoMac2/XHS data/",
            "priority": 0
        }
    )

    if create_response.status_code != 200:
        print(f"任务创建失败: {create_response.text}")
        return

    task_id = create_response.json()["task_id"]
    print(f"任务已创建，ID: {task_id}")

    # 轮询任务状态
    while True:
        status_response = requests.get(f"{BASE_URL}/tasks/{task_id}")
        if status_response.status_code != 200:
            print(f"状态查询失败: {status_response.text}")
            break

        data = status_response.json()
        print(
            f"\r当前状态: {data['status']} | 处理进度: {data['processed']}/{data['total']} | 成功: {data['success_count']} 失败: {data['failed_count']}",
            end="")

        if data["status"] in ("completed", "failed", "cancelled"):
            print("\n处理完成！")
            print(f"最终结果: {data}")
            break

        time.sleep(2)


if __name__ == "__main__":
    test_service()