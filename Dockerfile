# aws-cost-analyzer Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scanners/ ./scanners/
COPY analyzers/ ./analyzers/
COPY reporters/ ./reporters/
COPY cli.py .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set entrypoint
ENTRYPOINT ["python3", "cli.py"]
CMD ["--help"]