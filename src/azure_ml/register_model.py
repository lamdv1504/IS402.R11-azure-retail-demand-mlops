"""src/azure_ml/register_model.py — Đăng ký model từ Azure ML run vào Model Registry."""

import sys
from pathlib import Path

# Thêm root vào sys.path
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import Model
from src.azure_ml.connect import get_ml_client


def register(job_name: str, version: str = "1"):
    ml_client = get_ml_client()

    print("=" * 60)
    print(f"📦 BƯỚC 9: ĐĂNG KÝ MODEL VÀO AZURE ML MODEL REGISTRY")
    print(f"👉 Nguồn Run ID: {job_name}")
    print("=" * 60)

    # Lấy thông tin job và metrics nếu có
    job = ml_client.jobs.get(job_name)
    print(f"Trạng thái Job: {job.status}")

    if str(job.status).lower() not in ("completed", "jobstatus.completed"):
        print(f"⚠️ Cảnh báo: Job hiện tại đang ở trạng thái '{job.status}'.")

    # Đường dẫn artifact model từ Job outputs
    model_path = f"azureml://jobs/{job_name}/outputs/artifacts/paths/outputs/best_model.ubj"

    model = Model(
        name="m5-xgboost-mvp",
        version=version,
        path=model_path,
        type=AssetTypes.CUSTOM_MODEL,
        description=(
            "XGBoost M5 MVP model — CA_1, 300 items, horizon=28 days. "
            "Trained on d_1..d_1885, validated on d_1886..d_1913. "
            "Được huấn luyện trên Azure ML Compute m5-cpu-cluster."
        ),
        tags={
            "task": "HI06",
            "algorithm": "xgboost",
            "data_version": "m5-ca1-300-v1",
            "local_model_version": "hi05-xgboost-cb3a08fa5e82",
            "scope": "CA_1, 300 items",
            "horizon": "28",
            "objective": "count:poisson",
            "val_mae": "1.03",
            "val_rmse": "2.03",
            "subset_rmsse": "0.721",
            "run_id": job_name,
        },
        properties={
            "training_job": job_name,
            "framework": "xgboost",
            "compute": "m5-cpu-cluster",
        },
    )

    print("\n⏳ Đang đăng ký Model vào Registry...")
    try:
        registered = ml_client.models.create_or_update(model)
    except Exception as e:
        # Nếu path artifact có định dạng khác (ví dụ qua default output)
        print(f"Thử phương án fallback path default: {e}")
        model.path = f"azureml://jobs/{job_name}/outputs/default/best_model.ubj"
        registered = ml_client.models.create_or_update(model)

    print("\n" + "=" * 60)
    print("🎉 BƯỚC 9 THÀNH CÔNG: MODEL ĐÃ ĐƯỢC ĐĂNG KÝ VÀO REGISTRY!")
    print("=" * 60)
    print(f"👉 Model Name:    {registered.name}")
    print(f"👉 Model Version: {registered.version}")
    print(f"👉 Model ID:      {registered.id}")
    print("=" * 60)
    return registered


if __name__ == "__main__":
    job_id = sys.argv[1].strip() if len(sys.argv) > 1 else "olive_kitten_3w1vbdr333"
    register(job_id)
