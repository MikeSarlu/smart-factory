FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements from receiver folder
COPY receiver/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy receiver and lambda sources
COPY receiver/src/ ./src/
COPY aws/ ./aws/

CMD ["python", "src/app.py"]
