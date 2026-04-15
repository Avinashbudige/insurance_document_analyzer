# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build dependencies
    build-essential \
    libpq-dev \
    # OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    # Image processing
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    # Security and utilities
    curl \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/static /app/media /app/logs /app/temp

# Copy project files
COPY . .

# Create non-root user
RUN groupadd -r django && useradd -r -g django django \
    && chown -R django:django /app

# Switch to non-root user
USER django

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Start script
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]