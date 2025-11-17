# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DAGSTER_HOME=/opt/dagster

# Create app directory
WORKDIR /opt/dagster

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY uv.lock ./

# Install uv for fast Python package management
RUN pip install uv

# Install dependencies using uv
RUN uv sync --frozen --no-install-project

# Install dagster-webserver for production
RUN uv add dagster-webserver

# Expose port 3000 for Dagster webserver
EXPOSE 3000

# Run Dagster webserver
CMD ["uv", "run", "dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]
