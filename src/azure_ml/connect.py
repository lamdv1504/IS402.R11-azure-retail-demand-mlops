"""src/azure_ml/connect.py — Kết nối tới Azure ML Workspace."""

import json
from pathlib import Path
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential


def get_ml_client(custom_path: str | None = None) -> MLClient:
    """Tạo MLClient bằng DefaultAzureCredential và config.json."""
    credential = DefaultAzureCredential()

    # 1. Nếu truyền đường dẫn tùy chỉnh
    if custom_path and Path(custom_path).is_file():
        return MLClient.from_config(credential=credential, path=custom_path)

    # 2. Kiểm tra file config.json ở gốc repo
    root_config = Path(__file__).resolve().parents[2] / "config.json"
    if root_config.is_file():
        try:
            return MLClient.from_config(credential=credential, path=str(root_config))
        except Exception:
            config = json.loads(root_config.read_text(encoding="utf-8"))
            return MLClient(
                credential=credential,
                subscription_id=config["subscription_id"],
                resource_group_name=config["resource_group"],
                workspace_name=config["workspace_name"],
            )

    # 3. Dò tìm tự động theo SDK mặc định
    return MLClient.from_config(credential=credential)


if __name__ == "__main__":
    print("⏳ Đang kết nối tới Azure ML Workspace...")
    client = get_ml_client()
    ws = client.workspaces.get(client.workspace_name)
    print("=" * 50)
    print(f"✅ Kết nối thành công Workspace: {ws.name}")
    print(f"   Vùng (Location): {ws.location}")
    print(f"   Resource Group:  {ws.resource_group}")
    print("=" * 50)
