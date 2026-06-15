FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY receiver/requirements.txt ./receiver/requirements.txt
RUN pip install --no-cache-dir -r receiver/requirements.txt

COPY receiver/src/ ./receiver/src/
COPY aws/ ./aws/

CMD ["python", "receiver/src/app.py"]
