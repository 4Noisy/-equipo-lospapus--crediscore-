# syntax=docker/dockerfile:1
# CrediScore · scoring-api · S07
# Multi-stage: build con Python completo -> runtime distroless sin shell, como nonroot.

# --- build: instala dependencias en /deps ---
# 3.11 porque es la versión de Python que trae distroless python3-debian12;
# si se compila con otra versión, el runtime no encuentra los paquetes.
FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/deps -r requirements.txt

# --- runtime: mínimo, sin shell ni pip ---
FROM gcr.io/distroless/python3-debian12:nonroot
WORKDIR /app
COPY --from=build /deps /app/deps
COPY src/ ./src/
ENV PYTHONPATH=/app/deps \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
USER nonroot
EXPOSE 8080
ENTRYPOINT ["python3", "-m", "src.main"]
