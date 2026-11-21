"""src/azure_ml/submit_job.py — Submit HI06 training job lên Azure ML."""

import sys
import time
from pathlib import Path

# Thêm thư mục gốc vào sys.path
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from azure.ai.ml import Input, command
from azure.ai.ml.entities import Environment
from src.azure_ml.connect import get_ml_client


def submit():
    ml_client = get_ml_client()
    curr_dir = Path(__file__).resolve().parent

    print("=" * 60)
    print("🚀 BƯỚC 7: SUBMIT TRAINING JOB LÊN AZURE ML")
    print("=" * 60)

    # 1. Kiểm tra trạng thái máy ảo Compute
    compute_name = "m5-cpu-cluster"
    print(f"\n🔍 Đang kiểm tra Compute '{compute_name}'...")
    try:
        compute = ml_client.compute.get(compute_name)
        state_str = str(getattr(compute, "state", "")).lower()
        print(f"   Trạng thái hiện tại: {compute.state}")

        if "stop" in state_str:
            print(f"⚡ Compute đang ở trạng thái Stopped. Đang gửi lệnh khởi động (Start)...")
            ml_client.compute.begin_start(compute_name)
            print("⏳ Đã gửi lệnh bật máy ảo, tiến hành submit job...")
        else:
            print("✅ Compute đã sẵn sàng hoạt động!")
    except Exception as e:
        print(f"⚠️ Kiểm tra compute: {e}")

    # 2. Khởi tạo/Cập nhật Environment
    print("\n📦 Đang chuẩn bị Environment 'm5-xgboost-env'...")
    env = Environment(
        name="m5-xgboost-env",
        description="Môi trường huấn luyện XGBoost cho M5 Retail Forecasting",
        conda_file=str(curr_dir / "environment.yml"),
        image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu20.04:latest",
    )

    # 3. Định nghĩa Command Job
    print("\n🛠️ Đang cấu hình Command Job...")
    job = command(
        code=str(curr_dir),  # Đẩy toàn bộ source trong src/azure_ml/ lên
        command="python aml_train.py --data-path ${{inputs.data}} --config-path ${{inputs.config}}",
        inputs={
            "data": Input(type="uri_file", path="azureml:m5-processed-data:1"),
            "config": Input(type="uri_folder", path="azureml:m5-training-config:1"),
        },
        environment=env,
        compute=compute_name,
        display_name="HI06-xgboost-m5-mvp",
        experiment_name="m5-retail-demand-forecasting",
        description="HI06: Train XGBoost trên M5 MVP (CA_1, 300 items, horizon=28)",
        tags={
            "task": "HI06",
            "model": "xgboost",
            "data_version": "m5-ca1-300-v1",
            "scope": "CA_1-300items",
            "author": "Hieu",
        },
    )

    # 4. Submit Job lên Azure ML Workspace
    print("\n🚀 Đang gửi Job lên Azure ML Workspace...")
    returned_job = ml_client.jobs.create_or_update(job)

    print("\n" + "=" * 60)
    print("🎉 BƯỚC 7 THÀNH CÔNG: JOB ĐÃ ĐƯỢC SUBMIT LÊN AZURE ML!")
    print("=" * 60)
    print(f"👉 Run ID / Job Name: {returned_job.name}")
    print(f"👉 Display Name:      {returned_job.display_name}")
    print(f"👉 Status:            {returned_job.status}")
    print(f"👉 Experiment:        {returned_job.experiment_name}")
    print(f"👉 Studio URL:")
    print(f"   {returned_job.studio_url}")
    print("=" * 60)
    print("📌 Bạn hãy lưu lại Run ID để dùng cho việc đăng ký Model ở Bước 9.")

    return returned_job


if __name__ == "__main__":
    submit()
