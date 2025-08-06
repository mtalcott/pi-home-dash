FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    python3-dev \
    build-essential \
    chromium \
    xvfb \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY test_setup.py .
COPY README.md .

# Create necessary directories
RUN mkdir -p /app/cache /app/temp /var/log

# Set environment variables
ENV PYTHONPATH=/app/src
ENV DISPLAY=:99

# Create a startup script
RUN echo '#!/bin/bash\n\
# Start virtual display\n\
Xvfb :99 -screen 0 1920x1080x24 &\n\
# Run the application\n\
exec "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "src/main.py", "--test"]
