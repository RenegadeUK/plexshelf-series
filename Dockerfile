FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
# Copy static assets (icons, etc.) for Flask static serving
COPY src/static/ ./src/static/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create config and data directories
RUN mkdir -p /config /data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose web UI port
EXPOSE 8080

# Set entrypoint
CMD ["python", "src/main.py"]
