FROM python:3.12-slim

WORKDIR /app

# Ensure the root user's home directory exists and is writable
# This resolves issues where git config --global might fail in minimal images
RUN mkdir -p /root && chmod 777 /root  
ENV HOME /root

# Create a writable .gitconfig file for the injected command (keep this)
RUN touch /root/.gitconfig && chmod 666 /root/.gitconfig

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    wget\
    && rm -rf /var/lib/apt/lists/*

# Install uv - get the latest version from uv's GitHub releases
# We download the pre-compiled binary for Linux (musl) x86_64 and move it to /usr/local/bin
# Adjust the UV_VERSION if you want a specific one
ENV UV_VERSION="0.7.13" 
# Check https://github.com/astral-sh/uv/releases for the latest stable version
RUN curl -LO "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-musl.tar.gz" \
    && tar -xzf "uv-x86_64-unknown-linux-musl.tar.gz" \
    && mv uv-x86_64-unknown-linux-musl/uv /usr/local/bin/uv \
    && rm -rf uv-x86_64-unknown-linux-musl.tar.gz uv-x86_64-unknown-linux-musl

# COPY requirements.txt ./
COPY pyproject.toml ./
COPY src/ ./src/
COPY data/ ./data
COPY uv.lock ./

RUN mkdir -p models && chmod -R 777 models

# RUN pip3 install -r requirements.txt
RUN uv sync
ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]