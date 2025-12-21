FROM python:3.11-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

EXPOSE 8000

# Run uvicorn server (PORT is set by Render)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
