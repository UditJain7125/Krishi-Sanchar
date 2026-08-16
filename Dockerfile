FROM python:3.11-slim

# System libraries needed by opencv-python and a few ML libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching — only reinstalls if requirements change)
COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

# Copy the entire project (all 7 service folders) into the image
COPY . .

# Actual command is supplied per-service in docker-compose.yml
