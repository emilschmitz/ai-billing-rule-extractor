FROM python:3.11-slim

# Install uv system-wide
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy pyproject.toml and uv.lock
COPY pyproject.toml uv.lock ./

# Fast install
RUN uv sync --frozen

# Copy source and data
COPY rules_extractor/ ./
COPY data/ ./data/
COPY .streamlit/ ./.streamlit/

CMD ["uv", "run", "streamlit", "run", "frontend.py", "--browser.gatherUsageStats", "false", "--server.headless", "true"]
