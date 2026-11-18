"""Inference boundary for HI05's model handoff in GĐ3."""


class ModelNotReadyError(RuntimeError):
    pass


def model_loaded() -> bool:
    return False


def predict(*, store_id: str, item_id: str, horizon: int):
    raise ModelNotReadyError("Mô hình dự báo chưa được bàn giao. Vui lòng thử lại sau.")
