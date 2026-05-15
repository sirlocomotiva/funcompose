# Stage 1: build React
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: runtime
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend /app/dist ./static/

VOLUME ["/data"]
EXPOSE 8080

ENV DATA_PATH=/data

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
