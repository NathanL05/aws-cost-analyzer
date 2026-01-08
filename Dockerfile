# =============================================================================
# Stage 1: Builder - Install dependencies and run tests
# =============================================================================
FROM python:3.11-slim AS builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install production dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --user --no-cache-dir --no-warn-script-location -r requirements-dev.txt

# Copy application code
COPY scanners/ ./scanners/
COPY analyzers/ ./analyzers/
COPY reporters/ ./reporters/
COPY cli.py .
COPY tests/ ./tests/

# Run tests to ensure everything works
RUN python -m pytest tests/ -v

# =============================================================================
# Stage 2: Runtime - Minimal image with only what's needed
# =============================================================================
FROM python:3.11-slim

# Install runtime system dependencies (if any)
# Currently none needed, but keep for future

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Install ONLY production dependencies (not test deps from builder)
COPY requirements.txt .
RUN pip install --user --no-cache-dir --no-warn-script-location -r requirements.txt && \
    mv /root/.local /home/appuser/.local && \
    chown -R appuser:appuser /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser scanners/ ./scanners/
COPY --chown=appuser:appuser analyzers/ ./analyzers/
COPY --chown=appuser:appuser reporters/ ./reporters/
COPY --chown=appuser:appuser cli.py .

# Switch to non-root user
USER appuser

# Add user's local bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Set Python to run in unbuffered mode (better for logs)
ENV PYTHONUNBUFFERED=1

# Health check (optional but good practice)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import boto3; print('healthy')" || exit 1

# Set entrypoint
ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]