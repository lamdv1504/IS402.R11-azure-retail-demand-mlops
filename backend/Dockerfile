FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-ml.txt /app/requirements-ml.txt
COPY requirements-data.txt /app/requirements-data.txt
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ /app/backend/
COPY src/ /app/src/
COPY artifacts/hi05/ /app/artifacts/hi05/
COPY reports/Hung/ /app/reports/Hung/

ENV PYTHONPATH="/app:/app/backend"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
