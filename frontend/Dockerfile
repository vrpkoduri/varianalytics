# ---------------------------------------------------------------------------
# Variance Agent — Frontend (React + Vite)
# Multi-stage build: Node 20 + Nginx
# Build context: project root (../)
# ---------------------------------------------------------------------------

# --- Single stage: Serve pre-built frontend with Nginx ---
# Build is done locally (npm run build) and dist/ is committed to git.
# This avoids npm ci inside Docker, which fails behind corporate SSL proxies.
FROM nginx:alpine

COPY frontend/dist /usr/share/nginx/html

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
