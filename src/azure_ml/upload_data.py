"""src/azure_ml/upload_data.py — Đăng ký Data Assets lên Azure ML (An toàn, tự kiểm tra nếu đã có)."""

import sys
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import Data
from src.azure_ml.connect import get_ml_client


def register_assets():
    ml_client = get_ml_client()

    print("=" * 60)
    print("📤 BƯỚC 6: KIỂM TRA & ĐĂNG KÝ DATA ASSETS TRÊN AZURE ML")
    print("=" * 60)

    # 1. Kiểm tra / Đăng ký m5-processed-data
    data_name = "m5-processed-data"
    data_version = "1"
    try:
        existing_data = ml_client.data.get(data_name, version=data_version)
        print(f"\n✅ Data Asset '{data_name}:{data_version}' ĐÃ CÓ SẴN trên Workspace!")
        print(f"   Path: {existing_data.path}")
    except Exception:
        print(f"\n1️⃣ Đang đăng ký Data Asset '{data_name}:{data_version}'...")
        processed_blob_uri = (
            "azureml://datastores/ds_processed_data/paths/processed/m5/v1/m5_sales_processed.parquet"
        )
        data_asset = Data(
            name=data_name,
            version=data_version,
            description="M5 processed data CA_1 300 items (m5-ca1-300-v1) trên Azure Blob",
            path=processed_blob_uri,
            type=AssetTypes.URI_FILE,
            tags={
                "task": "HI06",
                "data_version": "m5-ca1-300-v1",
                "source": "H03-azure-blob",
                "store": "CA_1",
                "items": "300",
            },
        )
        created_data = ml_client.data.create_or_update(data_asset)
        print(f"✅ Đã tạo mới Data Asset: {created_data.name}:{created_data.version}")
        print(f"   Path: {created_data.path}")

    # 2. Kiểm tra / Đăng ký m5-training-config
    cfg_name = "m5-training-config"
    cfg_version = "1"
    try:
        existing_cfg = ml_client.data.get(cfg_name, version=cfg_version)
        print(f"\n✅ Config Asset '{cfg_name}:{cfg_version}' ĐÃ CÓ SẴN trên Workspace!")
        print(f"   Path: {existing_cfg.path}")
    except Exception:
        config_local_dir = root_dir / "artifacts" / "hi04"
        print(f"\n2️⃣ Đang upload và đăng ký Config Asset '{cfg_name}:{cfg_version}'...")
        config_asset = Data(
            name=cfg_name,
            version=cfg_version,
            description="Training config, feature schema và metadata từ HI04",
            path=str(config_local_dir),
            type=AssetTypes.URI_FOLDER,
            tags={
                "task": "HI06",
                "source": "HI04",
                "strategy": "direct_horizon_safe",
            },
        )
        created_config = ml_client.data.create_or_update(config_asset)
        print(f"✅ Đã tạo mới Config Asset: {created_config.name}:{created_config.version}")
        print(f"   Path: {created_config.path}")

    print("\n" + "=" * 60)
    print("🎉 BƯỚC 6: CẢ 2 ASSETS ĐÃ SẴN SÀNG TRÊN AZURE ML, KHÔNG CẦN CHẠY LẠI!")
    print("=" * 60)


if __name__ == "__main__":
    register_assets()
