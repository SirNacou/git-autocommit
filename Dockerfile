FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY cli.py /app/cli.py

# Create user matching host UID (typically 1000 for development)
# This allows git operations on mounted repositories without permission issues
RUN useradd -m -u ${UID:-1000} appuser \
    && mkdir -p /data /repos \
    && chown -R appuser:appuser /app /data /repos

USER appuser

CMD ["python", "-m", "src.main"]
