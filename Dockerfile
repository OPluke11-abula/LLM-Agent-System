# Stage 1: Build Frontend React App
FROM node:20-alpine AS frontend-builder
WORKDIR /app/viewer

# Copy package manifests first for efficient caching
COPY viewer/package*.json ./
RUN npm ci

# Copy frontend sources and compile
COPY viewer/ ./
RUN npm run build

# Stage 2: Final Production Backend
FROM python:3.11-slim
WORKDIR /app

# Set container Python environment invariants
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LAS_BIND_HOST=0.0.0.0
ENV LAS_ENABLE_STRIPE=false
ENV LAS_ENABLE_REDIS_SWARM=false
ENV LAS_ENABLE_MULTI_WORKER=false
ENV LAS_ENABLE_AUDIT_CONSENSUS=false

# Install curl for health check validation and git for worktree execution
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git && \
    rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create unprivileged system group and user for air-gapped container security
RUN groupadd -g 1001 lasgroup && \
    useradd -u 1001 -g lasgroup -m -s /bin/bash lasuser && \
    mkdir -p /app/.agent /app/agent_workspace/memory /app/workspace /app/viewer/dist && \
    chown -R lasuser:lasgroup /app

# Copy backend application and static assets
COPY . .
# Copy compiled frontend into place
COPY --from=frontend-builder /app/viewer/dist ./viewer/dist
RUN chown -R lasuser:lasgroup /app

# Switch to non-root execution
USER lasuser

EXPOSE 8000

# Configure robust health check against /v1/health
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/v1/health || exit 1

CMD ["python", "-m", "agent_workspace.server"]
