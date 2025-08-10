FROM python:3.9-slim

# Copy common setup script first
COPY scripts/common_setup.sh /tmp/common_setup.sh
RUN chmod +x /tmp/common_setup.sh

# Install system dependencies using shared function
RUN /tmp/common_setup.sh install_docker_system_deps

# Set working directory
WORKDIR /app

# Create common directory structure using shared function
RUN /tmp/common_setup.sh create_common_directories /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY test_setup.py .
COPY README.md .
COPY omni-epd.ini .

# Set environment variables using shared configuration
ENV PYTHONPATH=/app/src
ENV DISPLAY=:99
ENV DEBUG=false
ENV UPDATE_INTERVAL=300

# Create a startup script (Docker-specific)
RUN echo '#!/bin/bash\n\
# Start virtual display\n\
Xvfb :99 -screen 0 1920x1080x24 &\n\
# Run the application\n\
exec "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "src/main.py", "--test"]
