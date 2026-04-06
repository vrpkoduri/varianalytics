# ---------------------------------------------------------------------------
# Variance Agent — Frontend (React + Vite)
# Multi-stage build: Node 20 + Nginx
# Build context: project root (../)
# ---------------------------------------------------------------------------

# --- Stage 1: Build ---
FROM node:20-alpine AS build

WORKDIR /app

# Corporate proxy SSL workaround
RUN npm config set strict-ssl false

# Copy package files from frontend/ subdirectory
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Copy frontend source
COPY frontend/ .
RUN npm run build

# --- Stage 2: Serve with Nginx ---
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# SPA fallback: route all paths to index.html
RUN echo 'server { \
  listen 3000; \
  root /usr/share/nginx/html; \
  index index.html; \
  location / { \
    try_files $uri $uri/ /index.html; \
  } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
