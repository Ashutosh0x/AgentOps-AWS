# AgentOps Orchestrator Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY orchestrator/ ./orchestrator/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p orchestrator/demo_data

# Copy demo data
COPY orchestrator/demo_data/ ./orchestrator/demo_data/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check (using httpx which is already in requirements.txt)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/', timeout=5)" || exit 1

# Run the application
CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]

