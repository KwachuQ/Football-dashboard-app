FROM python:3.11-slim

FROM python:3.11-slim

# Install system deps and uv, then ensure uv is on PATH
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && echo 'export PATH="$PATH:/root/.local/bin:/root/.cargo/bin"' >> /etc/profile \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv || true \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD curl --fail http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]