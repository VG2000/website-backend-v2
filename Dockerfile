# Use an official Python runtime as a parent image
FROM python:3.12.3-slim-bookworm AS builder

# Set environment variables to ensure Python runs in unbuffered mode.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev python3-dev dnsutils telnet \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies in a virtual environment
RUN python -m venv /venv
COPY requirements.txt .
COPY requirements.prod.txt .
RUN /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install -r requirements.prod.txt

# Copy project files to the builder stage
COPY . .

# Collect static files
RUN /venv/bin/python manage.py collectstatic --noinput --verbosity 3

# Final stage
FROM python:3.12.3-slim-bookworm AS final

# Install necessary tools for DNS and connectivity checks in the final stage
RUN apt-get update \
    && apt-get install -y --no-install-recommends dnsutils telnet \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /venv /venv
COPY --from=builder /app /app

WORKDIR /app

# Set environment path to include venv bin
ENV PATH="/venv/bin:$PATH"

# Copy the entrypoint script and ensure it has execute permissions
COPY start-server.sh /usr/src/app/start-server.sh
RUN ls -l /usr/src/app/start-server.sh
RUN chmod +x /usr/src/app/start-server.sh

# Run the startup script
CMD ["/usr/src/app/start-server.sh"]



