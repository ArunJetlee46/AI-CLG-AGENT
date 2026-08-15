FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# ortools needed in the image: keep the Phase-10 CP-SAT solver fully functional
# (the rest of requirements-ml.txt is intentionally excluded to keep the image lean)
RUN pip install --no-cache-dir "ortools>=9.10"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
