FROM python:3.13.9-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create a non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --no-create-home appuser

# Set the working directory.
WORKDIR /app

# Install the application dependencies.
COPY uv.lock pyproject.toml README.md ./
RUN uv sync --frozen --no-cache --prerelease=allow

# Copy the application into the container.
COPY src/microsoft_agent_framework microsoft_agent_framework/

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

CMD ["/app/.venv/bin/fastapi", "run", "microsoft_agent_framework/infrastructure/api/main.py", "--port", "8000", "--host", "0.0.0.0"]

