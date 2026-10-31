FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code only (secrets come from the environment at runtime)
COPY app/ ./app/
COPY data/ ./data/
COPY frontend/ ./frontend/
COPY tests/ ./tests/
COPY pytest.ini setup.cfg ./

# Expose default port
EXPOSE 8000

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
