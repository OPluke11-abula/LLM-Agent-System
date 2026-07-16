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

# Install curl for health check validation
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY . .
# Copy compiled frontend into place
COPY --from=frontend-builder /app/viewer/dist ./viewer/dist

EXPOSE 8000

# Configure robust health check against /v1/health
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/v1/health || exit 1

# Start FastAPI API backend
ENV LAS_BIND_HOST=127.0.0.1
ENV LAS_ENABLE_STRIPE=false
ENV LAS_ENABLE_REDIS_SWARM=false
ENV LAS_ENABLE_MULTI_WORKER=false
ENV LAS_ENABLE_AUDIT_CONSENSUS=false
CMD ["python", "-m", "agent_workspace.server"]
