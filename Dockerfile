# --- Stage 1: Build the frontend ---
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend

# Leverage layer caching for node dependencies
COPY frontend/package*.json ./
RUN npm install

# Build the frontend production bundle (into frontend/dist)
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Backend & final runtime image ---
FROM python:3.12-slim
WORKDIR /app

# Create a dedicated unprivileged user for security
RUN useradd --create-home --shell /bin/bash appuser

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source code
COPY backend/ ./backend/

# Copy compiled frontend from Stage 1 into the location expected by app.py
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Set up data directory with correct ownership
RUN mkdir -p /app/backend/data && chown -R appuser:appuser /app

USER appuser

ENV FLASK_DEBUG=false \
    HOST=0.0.0.0

# Platforms like Render / Railway pass their assigned port dynamically via $PORT.
# If not passed, app.py defaults to 5000.
EXPOSE 5000

WORKDIR /app/backend
CMD ["python3", "app.py"]
