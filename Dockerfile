FROM python:3.11-slim


# Set working directory to /app/src for correct module imports
WORKDIR /app/src

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create config and data directories
RUN mkdir -p /config /data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose web UI port
EXPOSE 8080


# Set entrypoint to run from /app/src
CMD ["python", "main.py"]
