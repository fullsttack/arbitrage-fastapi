FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy project files
COPY pyproject.toml ./
COPY . .

# Install Python dependencies
RUN uv venv .venv
RUN . .venv/bin/activate && uv pip install -e .

# Collect static files
RUN . .venv/bin/activate && python manage.py collectstatic --noinput

# Run the application
CMD [".venv/bin/gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]